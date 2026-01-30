#!/usr/bin/env python3
"""
Scale to 100 decisions using the FastAPI ingestion endpoint.

This script:
1. Selects 100 balanced decisions (25/25/25/25)
2. Ingests them via the API
3. Tracks progress and errors
4. Validates the final corpus
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx
from src.fetcher.balanced_selector import BalancedSelector
from src.db.connection import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"
SELECTION_FILE = Path(__file__).parent.parent / "data" / "selection_100.json"


def check_api_health() -> bool:
    """Check if API is running."""
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info(f"✓ API is healthy: {response.json()}")
            return True
        else:
            logger.error(f"✗ API returned status {response.status_code}")
            return False
    except httpx.ConnectError:
        logger.error("✗ API is not running!")
        logger.error("Start it with: uvicorn api.main:app --reload")
        return False


def save_selection(decisions: list[dict], filepath: Path):
    """Save decision metadata to JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    metadata = []
    for d in decisions:
        metadata.append({
            "url": d["url"],
            "case_number": d["case_number"],
            "year": d["year"],
            "condition": d["condition"],
            "outcome": d["outcome"],
            "has_private_nexus": d.get("has_private_nexus", False),
            "has_exam_inadequacy": d.get("has_exam_inadequacy", False),
        })

    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✓ Saved selection to {filepath}")


def ingest_via_api(decision: dict) -> dict:
    """
    Ingest a decision via the API.

    Args:
        decision: Decision dict with url, case_number, year, text

    Returns:
        API response dict
    """
    # Use the ingest endpoint with URL
    payload = {
        "url": decision["url"],
        "case_number": decision["case_number"],
        "year": decision["year"]
    }

    response = httpx.post(
        f"{API_BASE_URL}/api/v1/ingest",
        json=payload,
        timeout=60  # LLM extraction can take time
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API returned {response.status_code}: {response.text}")


def validate_corpus():
    """Validate the final corpus meets all criteria."""
    logger.info("\n" + "="*70)
    logger.info("VALIDATING CORPUS")
    logger.info("="*70)

    conn = get_connection()

    # Total decisions
    cur = conn.execute("SELECT COUNT(*) FROM decisions")
    total = cur.fetchone()[0]
    logger.info(f"\nTotal decisions: {total}")

    # Outcome distribution
    cur = conn.execute("""
        SELECT outcome, COUNT(*) as count
        FROM issues
        GROUP BY outcome
        ORDER BY count DESC
    """)
    logger.info("\nOutcome distribution:")
    outcomes = {}
    for row in cur.fetchall():
        outcome, count = row
        outcomes[outcome] = count
        logger.info(f"  {outcome}: {count}")

    # Conditions
    cur = conn.execute("""
        SELECT c.name, COUNT(DISTINCT ic.issue_id) as issue_count
        FROM conditions c
        JOIN issue_conditions ic ON c.id = ic.condition_id
        GROUP BY c.name
        ORDER BY issue_count DESC
        LIMIT 10
    """)
    logger.info("\nTop conditions:")
    for row in cur.fetchall():
        condition, count = row
        logger.info(f"  {condition}: {count} issues")

    # Evidence types
    cur = conn.execute("""
        SELECT et.name, COUNT(*) as count
        FROM evidence_types et
        JOIN issue_evidence ie ON et.id = ie.evidence_type_id
        GROUP BY et.name
        ORDER BY count DESC
    """)
    logger.info("\nEvidence types:")
    for row in cur.fetchall():
        evidence, count = row
        logger.info(f"  {evidence}: {count}")

    # Special patterns (approximate check via text search)
    cur = conn.execute("""
        SELECT COUNT(*) FROM decisions
        WHERE raw_text ILIKE '%private medical opinion%'
           OR raw_text ILIKE '%private physician%'
           OR raw_text ILIKE '%independent medical%'
    """)
    private_nexus_count = cur.fetchone()[0]
    logger.info(f"\nDecisions with private nexus patterns: ~{private_nexus_count}")

    cur = conn.execute("""
        SELECT COUNT(*) FROM decisions
        WHERE raw_text ILIKE '%inadequate examination%'
           OR raw_text ILIKE '%inadequate for rating%'
           OR raw_text ILIKE '%examination is inadequate%'
    """)
    exam_inadequacy_count = cur.fetchone()[0]
    logger.info(f"Decisions with exam inadequacy patterns: ~{exam_inadequacy_count}")

    conn.close()

    # Validation checks
    logger.info("\n" + "="*70)
    logger.info("VALIDATION RESULTS")
    logger.info("="*70)

    checks = {
        "Total decisions >= 100": total >= 100,
        "Granted decisions >= 20": outcomes.get("Granted", 0) >= 20,
        "Denied decisions >= 20": outcomes.get("Denied", 0) >= 20,
        "Remanded decisions >= 20": outcomes.get("Remanded", 0) >= 20,
        "Private nexus >= 10": private_nexus_count >= 10,
        "Exam inadequacy >= 10": exam_inadequacy_count >= 10,
    }

    all_passed = True
    for check, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {check}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 ALL VALIDATION CHECKS PASSED!")
    else:
        logger.warning("\n⚠️  Some validation checks failed")

    return all_passed


def main():
    """Main execution flow."""
    start_time = datetime.now()

    logger.info("="*70)
    logger.info("SCALING TO 100 DECISIONS VIA API")
    logger.info("="*70)

    # Step 1: Check API health
    logger.info("\nStep 1: Checking API health...")
    if not check_api_health():
        logger.error("Exiting: API is not available")
        return 1

    # Step 2: Select 100 balanced decisions
    logger.info("\nStep 2: Selecting 100 balanced decisions...")
    logger.info("This may take 10-15 minutes due to rate limiting...")

    selector = BalancedSelector()
    decisions = selector.select_100_decisions()

    logger.info(f"\n✓ Selected {len(decisions)} decisions")

    # Save selection
    save_selection(decisions, SELECTION_FILE)

    # Step 3: Ingest via API
    logger.info("\nStep 3: Ingesting decisions via API...")
    logger.info("This will take 15-20 minutes (LLM extraction per decision)...")

    success_count = 0
    failed = []

    for i, decision in enumerate(decisions, 1):
        logger.info(f"\n[{i}/{len(decisions)}] Ingesting {decision['case_number']}...")

        try:
            result = ingest_via_api(decision)

            if result.get("success"):
                success_count += 1
                logger.info(f"  ✓ Success: {result['issues_extracted']} issues extracted")
            else:
                failed.append(decision['case_number'])
                logger.error(f"  ✗ Failed: {result.get('message')}")

        except Exception as e:
            failed.append(decision['case_number'])
            logger.error(f"  ✗ Failed: {e}")
            continue

        # Progress update every 10
        if i % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = (len(decisions) - i) * (elapsed / i)
            logger.info(f"\nProgress: {i}/{len(decisions)} ({i/len(decisions)*100:.1f}%)")
            logger.info(f"Elapsed: {elapsed:.1f}m | Estimated remaining: {remaining:.1f}m")

    # Step 4: Validate corpus
    logger.info("\nStep 4: Validating final corpus...")
    validate_corpus()

    # Summary
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total decisions processed: {len(decisions)}")
    logger.info(f"Successfully ingested: {success_count}")
    logger.info(f"Failed: {len(failed)}")
    if failed:
        logger.info(f"Failed case numbers: {', '.join(failed)}")
    logger.info(f"Total time: {elapsed_total:.1f} minutes")

    logger.info("\n✓ Scaling complete!")
    logger.info("\nNext steps:")
    logger.info("  1. Run validation: python scripts/validate.py")
    logger.info("  2. View API docs: http://localhost:8000/docs")
    logger.info("  3. Query similar cases via API")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
