#!/usr/bin/env python3
"""
Compute LEGALBENCH-inspired dual scores for all issues.

Run this after ingestion to score all issues for correctness and analysis depth.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection
from src.scoring import score_all_issues


def main():
    print("=" * 60)
    print("DUAL-SCORE EVALUATION (LEGALBENCH-inspired)")
    print("=" * 60)

    conn = get_connection()

    print("\nScoring all issues...")
    stats = score_all_issues(conn)

    print("\n" + "=" * 60)
    print("SCORING COMPLETE")
    print("=" * 60)
    print(f"\nTotal issues scored: {stats['scored']}")
    print(f"Average correctness score: {stats['avg_correctness']:.3f}")
    print(f"Average analysis depth score: {stats['avg_analysis']:.3f}")

    if stats['low_correctness']:
        print(f"\n! {len(stats['low_correctness'])} issues with correctness < 0.6:")
        print(f"  Issue IDs: {stats['low_correctness'][:10]}")
        if len(stats['low_correctness']) > 10:
            print(f"  ... and {len(stats['low_correctness']) - 10} more")

    if stats['low_analysis']:
        print(f"\n! {len(stats['low_analysis'])} issues with analysis depth < 0.5:")
        print(f"  Issue IDs: {stats['low_analysis'][:10]}")
        if len(stats['low_analysis']) > 10:
            print(f"  ... and {len(stats['low_analysis']) - 10} more")

    # Show some examples
    print("\n" + "=" * 60)
    print("SAMPLE SCORED ISSUES")
    print("=" * 60)

    cur = conn.execute("""
        SELECT
            i.id,
            i.outcome,
            c.name as condition,
            i.correctness_score,
            i.analysis_depth_score
        FROM issues i
        LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
        LEFT JOIN conditions c ON ic.condition_id = c.id
        WHERE i.correctness_score IS NOT NULL
        ORDER BY (i.correctness_score + i.analysis_depth_score) DESC
        LIMIT 5
    """)

    print("\nTop 5 highest-scoring issues:")
    for row in cur.fetchall():
        issue_id, outcome, condition, correctness, analysis = row
        print(f"  Issue {issue_id}: {outcome} - {condition or 'N/A'}")
        print(f"    Correctness: {correctness:.3f} | Analysis: {analysis:.3f}")

    cur = conn.execute("""
        SELECT
            i.id,
            i.outcome,
            c.name as condition,
            i.correctness_score,
            i.analysis_depth_score
        FROM issues i
        LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
        LEFT JOIN conditions c ON ic.condition_id = c.id
        WHERE i.correctness_score IS NOT NULL
        ORDER BY i.correctness_score ASC
        LIMIT 5
    """)

    print("\nLowest correctness scores (potential extraction errors):")
    for row in cur.fetchall():
        issue_id, outcome, condition, correctness, analysis = row
        print(f"  Issue {issue_id}: {outcome} - {condition or 'N/A'}")
        print(f"    Correctness: {correctness:.3f} | Analysis: {analysis:.3f}")

    conn.close()

    print("\nScores saved to database (issues.correctness_score, issues.analysis_depth_score)")


if __name__ == "__main__":
    main()
