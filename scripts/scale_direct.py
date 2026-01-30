#!/usr/bin/env python3
"""
Scale to 100 decisions using direct Python ingestion (bypass API).

Faster and simpler than API-based ingestion.
"""
import sys
from pathlib import Path
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.fetcher.balanced_selector import BalancedSelector
from src.extraction.gemini import extract_entities
from src.graph.loader import load_decision
from src.db.connection import get_connection, init_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main execution."""
    start_time = datetime.now()

    logger.info("="*70)
    logger.info("SCALING TO 100 DECISIONS (DIRECT INGESTION)")
    logger.info("="*70)

    # Initialize database
    logger.info("\nStep 1: Initializing database...")
    conn = get_connection()
    init_schema(conn)
    logger.info("  [PASS] Database ready")

    # Test Gemini API key
    logger.info("\nStep 2: Testing Gemini API key...")
    try:
        from google import genai
        from google.genai import types
        import os

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'OK'",
            config=types.GenerateContentConfig(temperature=0.1)
        )
        logger.info(f"  [PASS] API key works: {response.text}")
    except Exception as e:
        logger.error(f"  [FAIL] API key error: {e}")
        return 1

    # Select 100 decisions
    logger.info("\nStep 3: Selecting 100 balanced decisions...")
    logger.info("  This may take 10-20 minutes...")

    selector = BalancedSelector()
    decisions = selector.select_100_decisions()

    logger.info(f"\n  [PASS] Selected {len(decisions)} decisions")

    # Ingest decisions
    logger.info("\nStep 4: Ingesting decisions...")
    logger.info("  This may take 15-25 minutes (LLM extraction)...")

    success_count = 0
    failed = []

    for i, decision in enumerate(decisions, 1):
        logger.info(f"\n[{i}/{len(decisions)}] {decision['case_number']}...")

        try:
            # Extract entities
            extraction = extract_entities(decision["text"])

            # Load to database
            load_decision(
                conn=conn,
                decision_id=decision["case_number"],
                raw_text=decision["text"],
                decision_date=decision["parsed"].get("decision_date"),
                extraction=extraction
            )
            conn.commit()

            success_count += 1
            logger.info(f"  [PASS] {len(extraction.issues)} issues extracted")

        except Exception as e:
            conn.rollback()
            failed.append(decision["case_number"])
            logger.error(f"  [FAIL] {e}")
            continue

        # Progress update
        if i % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = (len(decisions) - i) * (elapsed / i)
            logger.info(f"\nProgress: {i}/{len(decisions)} ({i/len(decisions)*100:.1f}%)")
            logger.info(f"Elapsed: {elapsed:.1f}m | Remaining: ~{remaining:.1f}m")

    conn.close()

    # Summary
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total decisions: {len(decisions)}")
    logger.info(f"Successfully ingested: {success_count}")
    logger.info(f"Failed: {len(failed)}")
    if failed:
        logger.info(f"Failed cases: {', '.join(failed[:10])}")
    logger.info(f"Total time: {elapsed_total:.1f} minutes")

    logger.info("\n[PASS] Scaling complete!")
    logger.info("\nNext: python scripts/validate.py")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
