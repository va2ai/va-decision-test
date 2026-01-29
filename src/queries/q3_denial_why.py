import psycopg

def analyze_denial(conn: psycopg.Connection, issue_id: int) -> dict:
    """
    Analyze why an issue was denied by looking for missing evidence.

    Returns missing evidence types and exam adequacy passages.
    """
    result = {
        "issue_id": issue_id,
        "outcome": None,
        "missing_evidence": [],
        "present_evidence": [],
        "exam_passages": [],
    }

    # Get outcome
    cur = conn.execute("SELECT outcome FROM issues WHERE id = %s", (issue_id,))
    if row := cur.fetchone():
        result["outcome"] = row[0]

    # Get present evidence types
    cur = conn.execute("""
        SELECT et.name FROM evidence_types et
        JOIN issue_evidence ie ON et.id = ie.evidence_type_id
        WHERE ie.issue_id = %s
    """, (issue_id,))
    result["present_evidence"] = [row[0] for row in cur.fetchall()]

    # Determine missing evidence
    all_evidence = ["STR", "VA_EXAM", "PRIVATE_OPINION", "LAY_EVIDENCE"]
    result["missing_evidence"] = [e for e in all_evidence if e not in result["present_evidence"]]

    # Get exam adequacy passages
    cur = conn.execute("""
        SELECT p.text FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        WHERE ip.issue_id = %s AND p.tag = 'EXAM_ADEQUACY'
    """, (issue_id,))
    result["exam_passages"] = [row[0] for row in cur.fetchall()]

    return result
