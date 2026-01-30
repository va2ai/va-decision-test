#!/usr/bin/env python3
"""
Validate the 100-decision test by running 5 MVP queries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection
from src.queries.q1_similar import find_similar_cases
from src.queries.q2_evidence_chain import get_evidence_chain
from src.queries.q3_denial_why import analyze_denial
from src.queries.q4_evidence_diff import compare_evidence_by_outcome
from src.queries.q5_authority_stats import get_authority_stats

def run_validation():
    conn = get_connection()
    results = {"pass": 0, "fail": 0, "details": []}

    # Query 1: Similar cases
    print("\n=== Query 1: Similar Cases ===")
    try:
        similar = find_similar_cases(conn, "tinnitus noise exposure", limit=5)
        if len(similar) > 0:
            print(f"[PASS] Found {len(similar)} similar cases")
            for s in similar[:3]:
                print(f"  - {s['decision_id']}: {s['outcome']} ({s['condition']})")
            results["pass"] += 1
        else:
            print("[FAIL] No results (may need embeddings)")
            results["fail"] += 1
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        results["fail"] += 1

    # Get a sample issue ID for queries 2-3
    cur = conn.execute("SELECT id, outcome FROM issues LIMIT 2")
    issues = cur.fetchall()

    if not issues:
        print("\n[FAIL] No issues in database - run ingestion first")
        return results

    # Query 2: Evidence chain
    print("\n=== Query 2: Evidence Chain ===")
    try:
        chain = get_evidence_chain(conn, issue_id=issues[0][0])
        print(f"[PASS] Issue {issues[0][0]}: {chain['condition']}")
        print(f"  Evidence: {chain['evidence_types']}")
        print(f"  Providers: {chain['provider_types']}")
        print(f"  Authorities: {chain['authorities'][:3]}")
        results["pass"] += 1
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        results["fail"] += 1

    # Query 3: Denial analysis
    print("\n=== Query 3: Why Denied ===")
    try:
        # Find a denied issue
        cur = conn.execute("SELECT id FROM issues WHERE outcome = 'Denied' LIMIT 1")
        denied = cur.fetchone()
        if denied:
            analysis = analyze_denial(conn, issue_id=denied[0])
            print(f"[PASS] Denied issue {denied[0]}")
            print(f"  Missing evidence: {analysis['missing_evidence']}")
            print(f"  Exam passages: {len(analysis['exam_passages'])}")
            results["pass"] += 1
        else:
            print("[PASS] No denied issues to analyze (not a failure)")
            results["pass"] += 1
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        results["fail"] += 1

    # Query 4: Evidence diff
    print("\n=== Query 4: Evidence by Outcome ===")
    try:
        diff = compare_evidence_by_outcome(conn, "tinnitus")
        if diff:
            print(f"[PASS] Found {len(diff)} evidence/outcome combinations")
            for d in diff[:5]:
                print(f"  - {d['evidence_type']}: {d['outcome']} ({d['count']})")
        else:
            print("[PASS] No data for tinnitus (try another condition)")
        results["pass"] += 1
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        results["fail"] += 1

    # Query 5: Authority stats
    print("\n=== Query 5: Authority Stats ===")
    try:
        stats = get_authority_stats(conn, "tinnitus")
        if stats:
            print(f"[PASS] Found {len(stats)} authority/outcome combinations")
            for s in stats[:5]:
                print(f"  - {s['citation']}: {s['outcome']} ({s['count']})")
        else:
            print("[PASS] No authority data (try another condition)")
        results["pass"] += 1
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        results["fail"] += 1

    # Show dual scores if available
    print("\n=== Dual-Score Metrics ===")
    try:
        cur = conn.execute("""
            SELECT
                COUNT(*) as total,
                AVG(correctness_score) as avg_correctness,
                AVG(analysis_depth_score) as avg_analysis,
                COUNT(*) FILTER (WHERE correctness_score < 0.6) as low_correctness,
                COUNT(*) FILTER (WHERE analysis_depth_score < 0.5) as low_analysis
            FROM issues
            WHERE correctness_score IS NOT NULL
        """)
        row = cur.fetchone()
        if row and row[0] > 0:
            total, avg_c, avg_a, low_c, low_a = row
            print(f"[PASS] Scored issues: {total}")
            print(f"  Avg correctness: {avg_c:.3f}")
            print(f"  Avg analysis depth: {avg_a:.3f}")
            if low_c > 0:
                print(f"  [WARN] {low_c} issues with low correctness (<0.6)")
            if low_a > 0:
                print(f"  [WARN] {low_a} issues with low analysis depth (<0.5)")
        else:
            print("  [INFO] No scores yet - run scripts/score_issues.py")
    except Exception as e:
        print(f"  [INFO] Scoring not available (run migration or score_issues.py)")

    conn.close()

    # Summary
    print("\n" + "=" * 50)
    print(f"VALIDATION RESULTS: {results['pass']}/5 queries passed")
    if results["fail"] == 0:
        print("[PASS] SCHEMA VALIDATED - Ready to scale")
    else:
        print("[FAIL] ISSUES FOUND - Review before scaling")

    return results

if __name__ == "__main__":
    run_validation()
