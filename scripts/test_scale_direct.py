#!/usr/bin/env python3
"""Test scaling with 10 decisions using direct ingestion."""
import sys
from pathlib import Path
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.fetcher.search import search_bva, fetch_decision_text
from src.fetcher.parser import parse_decision
from src.extraction.gemini import extract_entities
from src.graph.loader import load_decision
from src.db.connection import get_connection, init_schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main():
    start_time = datetime.now()

    logger.info("Testing direct ingestion with 10 decisions...")

    # Initialize
    conn = get_connection()
    init_schema(conn)

    # Search
    logger.info("\nSearching for decisions...")
    results = search_bva("tinnitus granted", year=2024, max_results=10)
    logger.info(f"[PASS] Found {len(results)} decisions")

    # Ingest
    logger.info("\nIngesting...")
    success = 0

    for i, r in enumerate(results[:10], 1):
        logger.info(f"\n[{i}/10] {r['case_number']}...")

        try:
            text = fetch_decision_text(r["url"])
            parsed = parse_decision(text)
            extraction = extract_entities(text)

            load_decision(
                conn=conn,
                decision_id=r["case_number"],
                raw_text=text,
                decision_date=parsed.get("decision_date"),
                extraction=extraction
            )
            conn.commit()

            logger.info(f"  [PASS] {len(extraction.issues)} issues")
            success += 1

        except Exception as e:
            conn.rollback()
            logger.error(f"  [FAIL] {e}")

    conn.close()

    elapsed = (datetime.now() - start_time).total_seconds() / 60
    logger.info(f"\n[PASS] Complete: {success}/10 in {elapsed:.1f}m")
    logger.info("\nReady to scale: python scripts/scale_direct.py")


if __name__ == "__main__":
    main()
