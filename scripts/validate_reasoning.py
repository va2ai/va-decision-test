#!/usr/bin/env python3
"""
LEGALBENCH-style validation suite for VA decision reasoning.

Tests rule-application, fact-to-element connections, and reasoning quality.
Runs all 5 MVP queries with assertions that catch logical errors.
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


class ReasoningValidator:
    """LEGALBENCH-style validator for reasoning quality."""

    def __init__(self, conn):
        self.conn = conn
        self.passes = 0
        self.failures = 0
        self.errors = []

    def assert_rule(self, condition: bool, message: str):
        """Assert a LEGALBENCH-style rule."""
        if condition:
            self.passes += 1
            print(f"  [PASS] {message}")
        else:
            self.failures += 1
            self.errors.append(message)
            print(f"  [FAIL] {message}")

    def test_q1_similarity(self):
        """Test: Interpretation + reasoning similarity."""
        print("\n=== Q1: Similarity (Interpretation + Reasoning) ===")

        similar = find_similar_cases(self.conn, "tinnitus noise exposure", limit=5)

        self.assert_rule(
            len(similar) > 0,
            "Found similar cases for query"
        )

        # Rule: Similar cases should have passages (not just empty links)
        has_passage = any(s.get('passage') for s in similar)
        self.assert_rule(
            has_passage or len(similar) == 0,
            "Similar cases include passage content (not just IDs)"
        )

    def test_q2_evidence_chain(self):
        """Test: Rule-application (fact -> element)."""
        print("\n=== Q2: Evidence Chain (Fact -> Element) ===")

        # Get all granted issues
        cur = self.conn.execute("""
            SELECT id, outcome FROM issues
            WHERE outcome = 'Granted'
            LIMIT 10
        """)
        granted = cur.fetchall()

        if not granted:
            print("  [WARN] No granted issues to test")
            return

        violation_count = 0
        for issue_id, outcome in granted:
            chain = get_evidence_chain(self.conn, issue_id)

            # Rule: Granted issues MUST cite ≥1 authority OR have medical opinion
            has_authority = len(chain.get('authorities', [])) > 0
            has_medical_opinion = any(
                p.get('tag') == 'MEDICAL_OPINION'
                for p in chain.get('passages', [])
            )

            if not (has_authority or has_medical_opinion):
                violation_count += 1

        self.assert_rule(
            violation_count == 0,
            f"All granted issues cite authority OR medical opinion (violations: {violation_count}/{len(granted)})"
        )

    def test_q3_denial_reasoning(self):
        """Test: Rule-application (negative case)."""
        print("\n=== Q3: Denial Reasoning (Negative Case) ===")

        # Get all denied issues
        cur = self.conn.execute("""
            SELECT id FROM issues
            WHERE outcome = 'Denied'
            LIMIT 10
        """)
        denied = [row[0] for row in cur.fetchall()]

        if not denied:
            print("  [WARN] No denied issues to test")
            return

        no_explanation_count = 0
        for issue_id in denied:
            analysis = analyze_denial(self.conn, issue_id)

            # Rule: Denied issues MUST list ≥1 missing element OR have exam adequacy passage
            has_missing = len(analysis.get('missing_evidence', [])) > 0
            has_exam_passage = len(analysis.get('exam_passages', [])) > 0

            if not (has_missing or has_exam_passage):
                no_explanation_count += 1

        self.assert_rule(
            no_explanation_count == 0,
            f"All denied issues explain missing evidence (violations: {no_explanation_count}/{len(denied)})"
        )

        # Rule: No issue should have empty evidence AND confident outcome
        cur = self.conn.execute("""
            SELECT COUNT(*) FROM issues i
            WHERE i.outcome IN ('Granted', 'Denied')
            AND NOT EXISTS (
                SELECT 1 FROM issue_evidence ie WHERE ie.issue_id = i.id
            )
        """)
        confident_without_evidence = cur.fetchone()[0]

        self.assert_rule(
            confident_without_evidence == 0,
            f"No confident outcomes without evidence (violations: {confident_without_evidence})"
        )

    def test_q4_cross_case_reasoning(self):
        """Test: Cross-case reasoning."""
        print("\n=== Q4: Evidence Diff (Cross-Case Reasoning) ===")

        # Test across multiple conditions
        conditions = ["tinnitus", "ptsd", "sleep apnea"]
        tested = False

        for condition in conditions:
            diff = compare_evidence_by_outcome(self.conn, condition)
            if not diff:
                continue

            tested = True

            # Rule: Granted outcomes should generally have more evidence variety
            granted_evidence = {d['evidence_type'] for d in diff if d['outcome'] == 'Granted'}
            denied_evidence = {d['evidence_type'] for d in diff if d['outcome'] == 'Denied'}

            if granted_evidence and denied_evidence:
                # This is informational, not a hard rule
                print(f"  [INFO] {condition}: Granted has {len(granted_evidence)} types, Denied has {len(denied_evidence)} types")

        self.assert_rule(
            tested,
            "Successfully compared evidence patterns across outcomes"
        )

    def test_q5_rule_recall(self):
        """Test: Rule-recall proxy."""
        print("\n=== Q5: Authority Stats (Rule-Recall Proxy) ===")

        stats = get_authority_stats(self.conn, "")  # All conditions

        self.assert_rule(
            len(stats) > 0,
            "Found legal authorities in decisions"
        )

        # Rule: Authority citations should be properly formatted
        malformed = 0
        for stat in stats[:20]:  # Check first 20
            citation = stat.get('citation', '')
            # Very basic check - should contain C.F.R. or U.S.C. or a case name
            if citation and not any(marker in citation for marker in ['C.F.R.', 'U.S.C.', 'v.', 'Va.']):
                malformed += 1

        self.assert_rule(
            malformed < len(stats[:20]) * 0.3,  # Allow up to 30% non-standard
            f"Most authorities are properly formatted (malformed: {malformed}/20)"
        )

    def test_rhetorical_understanding(self):
        """Test: Rhetorical understanding (new LEGALBENCH category)."""
        print("\n=== Bonus: Rhetorical Understanding ===")

        # Check if we have rhetorical passage tags
        cur = self.conn.execute("""
            SELECT tag, COUNT(*) FROM passages
            WHERE tag IN (
                'NEGATIVE_CREDIBILITY',
                'NO_NEXUS_FOUND',
                'BENEFIT_OF_DOUBT_APPLIED',
                'WEIGHING_OF_EVIDENCE'
            )
            GROUP BY tag
        """)

        rhetorical_tags = {row[0]: row[1] for row in cur.fetchall()}

        if rhetorical_tags:
            print(f"  [INFO] Found rhetorical passages: {rhetorical_tags}")
            self.assert_rule(
                True,
                "Rhetorical understanding tags detected"
            )
        else:
            print("  [INFO] No rhetorical tags yet (optional feature)")

    def run_all(self):
        """Run all validation tests."""
        print("\n" + "=" * 60)
        print("LEGALBENCH-STYLE REASONING VALIDATION")
        print("=" * 60)

        self.test_q1_similarity()
        self.test_q2_evidence_chain()
        self.test_q3_denial_reasoning()
        self.test_q4_cross_case_reasoning()
        self.test_q5_rule_recall()
        self.test_rhetorical_understanding()

        # Summary
        print("\n" + "=" * 60)
        total_tests = self.passes + self.failures
        pass_rate = (self.passes / total_tests * 100) if total_tests > 0 else 0

        print(f"RESULTS: {self.passes}/{total_tests} assertions passed ({pass_rate:.1f}%)")

        if self.failures == 0:
            print("[SUCCESS] ALL LEGALBENCH-STYLE RULES SATISFIED")
            print("  System demonstrates correct reasoning patterns")
        else:
            print(f"\n[FAIL] {self.failures} VIOLATIONS DETECTED:")
            for error in self.errors:
                print(f"  - {error}")

        return self.failures == 0


def main():
    conn = get_connection()
    validator = ReasoningValidator(conn)
    success = validator.run_all()
    conn.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
