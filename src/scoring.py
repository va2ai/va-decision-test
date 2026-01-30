"""
LEGALBENCH-inspired dual-score evaluation system.

Separates correctness (logical validity) from analysis depth (reasoning quality).
"""
from typing import Optional
import psycopg

def compute_correctness_score(
    conn: psycopg.Connection,
    issue_id: int,
    decision_text: Optional[str] = None
) -> float:
    """
    Compute correctness score (0.0-1.0) for an issue.

    Penalizes:
    - Outcome contradicts decision ORDER section
    - Evidence claimed but no passage tagged
    - Authority cited but not in decision text

    Args:
        conn: Database connection
        issue_id: Issue to score
        decision_text: Optional decision text for validation

    Returns:
        Score between 0.0 (many errors) and 1.0 (no errors)
    """
    score = 1.0
    penalties = []

    # Get issue details
    cur = conn.execute("""
        SELECT i.outcome, i.issue_text, d.raw_text
        FROM issues i
        JOIN decisions d ON i.decision_id = d.id
        WHERE i.id = %s
    """, (issue_id,))

    row = cur.fetchone()
    if not row:
        return 0.0

    outcome, issue_text, raw_text = row
    decision_text = decision_text or raw_text

    # Penalty 1: Check if evidence types claimed but no passages tagged
    cur = conn.execute("""
        SELECT COUNT(*) FROM issue_evidence WHERE issue_id = %s
    """, (issue_id,))
    evidence_count = cur.fetchone()[0]

    cur = conn.execute("""
        SELECT COUNT(*) FROM issue_passages WHERE issue_id = %s
    """, (issue_id,))
    passage_count = cur.fetchone()[0]

    if evidence_count > 0 and passage_count == 0:
        score -= 0.3
        penalties.append("evidence_claimed_no_passages")

    # Penalty 2: Check if authorities cited but not in decision text
    cur = conn.execute("""
        SELECT a.citation FROM authorities a
        JOIN decision_authorities da ON a.id = da.authority_id
        JOIN issues i ON da.decision_id = i.decision_id
        WHERE i.id = %s
    """, (issue_id,))

    authorities = [row[0] for row in cur.fetchall()]
    for auth in authorities:
        # Simple check - authority should appear in text
        if auth and auth not in decision_text:
            score -= 0.15
            penalties.append(f"authority_not_in_text:{auth[:20]}")
            break  # Only penalize once

    # Penalty 3: Outcome logic check
    # If outcome is "Granted" but no evidence, penalize
    if outcome == "Granted":
        if evidence_count == 0:
            score -= 0.4
            penalties.append("granted_without_evidence")

    # If outcome is "Denied" and we have strong evidence, that's suspicious
    if outcome == "Denied":
        # Check for MEDICAL_OPINION or PRIVATE_OPINION passages
        cur = conn.execute("""
            SELECT COUNT(*) FROM passages p
            JOIN issue_passages ip ON p.id = ip.passage_id
            WHERE ip.issue_id = %s
            AND p.tag IN ('MEDICAL_OPINION', 'PRIVATE_OPINION')
        """, (issue_id,))
        strong_evidence = cur.fetchone()[0]

        if strong_evidence > 0 and evidence_count >= 3:
            # This might be legitimate (examining physicians disagreed, etc)
            # So only a small penalty
            score -= 0.1
            penalties.append("denied_despite_strong_evidence")

    return max(0.0, min(1.0, score))


def compute_analysis_depth_score(
    conn: psycopg.Connection,
    issue_id: int
) -> float:
    """
    Compute analysis depth score (0.0-1.0) for an issue.

    Rewards:
    - Issue has ≥1 evidence type
    - Has ≥1 passage tagged REASONS_BASES or MEDICAL_OPINION
    - Denial has explicit missing-evidence explanation
    - Multiple passage types (shows comprehensive analysis)

    Args:
        conn: Database connection
        issue_id: Issue to score

    Returns:
        Score between 0.0 (minimal analysis) and 1.0 (comprehensive)
    """
    score = 0.0

    # Get outcome
    cur = conn.execute("SELECT outcome FROM issues WHERE id = %s", (issue_id,))
    row = cur.fetchone()
    if not row:
        return 0.0
    outcome = row[0]

    # Reward 1: Has evidence types (+0.3)
    cur = conn.execute("""
        SELECT COUNT(*) FROM issue_evidence WHERE issue_id = %s
    """, (issue_id,))
    evidence_count = cur.fetchone()[0]
    if evidence_count >= 1:
        score += 0.3

    # Reward 2: Has REASONS_BASES or MEDICAL_OPINION passage (+0.3)
    cur = conn.execute("""
        SELECT COUNT(*) FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        WHERE ip.issue_id = %s
        AND p.tag IN ('REASONS_BASES', 'MEDICAL_OPINION')
    """, (issue_id,))
    reasoning_count = cur.fetchone()[0]
    if reasoning_count >= 1:
        score += 0.3

    # Reward 3: For denials, check for explicit reasoning (+0.2)
    if outcome == "Denied":
        # Look for EXAM_ADEQUACY, NO_NEXUS_FOUND, or WEIGHING_OF_EVIDENCE tags
        cur = conn.execute("""
            SELECT COUNT(*) FROM passages p
            JOIN issue_passages ip ON p.id = ip.passage_id
            WHERE ip.issue_id = %s
            AND p.tag IN ('EXAM_ADEQUACY', 'NO_NEXUS_FOUND', 'WEIGHING_OF_EVIDENCE', 'NEGATIVE_CREDIBILITY')
        """, (issue_id,))
        denial_reasoning = cur.fetchone()[0]
        if denial_reasoning >= 1:
            score += 0.2

    # Reward 4: Multiple distinct passage types shows thorough analysis (+0.2)
    cur = conn.execute("""
        SELECT COUNT(DISTINCT p.tag) FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        WHERE ip.issue_id = %s
    """, (issue_id,))
    distinct_tags = cur.fetchone()[0]
    if distinct_tags >= 3:
        score += 0.2

    return min(1.0, score)


def score_all_issues(conn: psycopg.Connection) -> dict:
    """
    Compute scores for all issues in the database.

    Updates the issues table with correctness_score and analysis_depth_score.

    Returns:
        Summary statistics
    """
    cur = conn.execute("SELECT id FROM issues")
    issue_ids = [row[0] for row in cur.fetchall()]

    stats = {
        "total_issues": len(issue_ids),
        "scored": 0,
        "avg_correctness": 0.0,
        "avg_analysis": 0.0,
        "low_correctness": [],  # Issues with score < 0.6
        "low_analysis": [],      # Issues with score < 0.5
    }

    correctness_sum = 0.0
    analysis_sum = 0.0

    for issue_id in issue_ids:
        correctness = compute_correctness_score(conn, issue_id)
        analysis = compute_analysis_depth_score(conn, issue_id)

        # Update database
        conn.execute("""
            UPDATE issues
            SET correctness_score = %s, analysis_depth_score = %s
            WHERE id = %s
        """, (correctness, analysis, issue_id))

        correctness_sum += correctness
        analysis_sum += analysis
        stats["scored"] += 1

        if correctness < 0.6:
            stats["low_correctness"].append(issue_id)
        if analysis < 0.5:
            stats["low_analysis"].append(issue_id)

    conn.commit()

    if stats["scored"] > 0:
        stats["avg_correctness"] = correctness_sum / stats["scored"]
        stats["avg_analysis"] = analysis_sum / stats["scored"]

    return stats
