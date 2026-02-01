#!/usr/bin/env python3
"""
Test scaling with 10 decisions before running the full 100.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"


def test_scale():
    """Test ingestion of 10 decisions via API."""

    # Check API health
    logger.info("Checking API health...")
    try:
        r = httpx.get(f"{API_BASE_URL}/health", timeout=5)
        logger.info(f"✓ API healthy: {r.json()}")
    except Exception as e:
        logger.error(f"✗ API not available: {e}")
        return

    # Test search
    logger.info("\nTesting search...")
    r = httpx.post(f"{API_BASE_URL}/api/v1/search", json={
        "query": "tinnitus granted",
        "year": 2024,
        "max_results": 10
    }, timeout=30)

    results = r.json()["results"]
    logger.info(f"✓ Found {len(results)} decisions to test with")

    # Test ingestion of first 3
    logger.info("\nTesting ingestion of 3 decisions...")
    success_count = 0

    for i, decision in enumerate(results[:3], 1):
        logger.info(f"\n[{i}/3] Ingesting {decision['case_number']}...")

        try:
            r = httpx.post(
                f"{API_BASE_URL}/api/v1/ingest",
                json={
                    "url": decision["url"],
                    "case_number": decision["case_number"],
                    "year": decision["year"]
                },
                timeout=60
            )

            if r.status_code == 200:
                result = r.json()
                logger.info(f"  ✓ Success: {result['issues_extracted']} issues")
                success_count += 1
            else:
                logger.error(f"  ✗ Failed: {r.status_code} - {r.text[:100]}")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")

    # Summary
    logger.info("\n" + "="*60)
    logger.info(f"Test Results: {success_count}/3 successful")
    logger.info("="*60)

    if success_count == 3:
        logger.info("\n✓ All tests passed! Ready to scale to 100.")
        logger.info("\nRun: python scripts/scale_to_100.py")
    else:
        logger.warning("\n⚠ Some tests failed. Check the errors above.")


if __name__ == "__main__":
    test_scale()
