#!/usr/bin/env python3
"""
Ingestion pipeline: Select 100 decisions, extract entities, load to database.
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection, init_schema
from src.fetcher.selector import select_decisions, SELECTION_CRITERIA
from src.extraction.gemini import extract_entities
from src.graph.loader import load_decision

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "decisions"
SELECTION_FILE = Path(__file__).parent.parent / "data" / "selection.json"

def save_selection(decisions: list[dict]) -> None:
    """Save selected decisions to JSON for reproducibility."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Save metadata (without full text)
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

        # Save raw text to file
        text_file = DATA_DIR / f"{d['case_number']}.txt"
        text_file.write_text(d["text"], encoding="utf-8")

    SELECTION_FILE.write_text(json.dumps(metadata, indent=2))
    logger.info(f"Saved {len(metadata)} decisions to {SELECTION_FILE}")

def load_selection() -> list[dict]:
    """Load previously selected decisions."""
    if not SELECTION_FILE.exists():
        return []

    metadata = json.loads(SELECTION_FILE.read_text())
    decisions = []
    for m in metadata:
        text_file = DATA_DIR / f"{m['case_number']}.txt"
        if text_file.exists():
            m["text"] = text_file.read_text(encoding="utf-8")
            decisions.append(m)

    return decisions

def run_ingestion(skip_selection: bool = False, limit: int = 100) -> None:
    """Run the full ingestion pipeline."""

    # Step 1: Select decisions (or load existing)
    if skip_selection and SELECTION_FILE.exists():
        logger.info("Loading existing selection...")
        decisions = load_selection()
    else:
        logger.info("Selecting decisions...")
        decisions = select_decisions(max_per_bucket=5)
        decisions = decisions[:limit]
        save_selection(decisions)

    logger.info(f"Working with {len(decisions)} decisions")

    # Step 2: Initialize database
    logger.info("Initializing database...")
    conn = get_connection()
    init_schema(conn)

    # Step 3: Extract and load each decision
    success_count = 0
    for i, decision in enumerate(decisions):
        logger.info(f"Processing {i+1}/{len(decisions)}: {decision['case_number']}")

        try:
            # Extract entities
            extraction = extract_entities(decision["text"])

            # Load to database
            load_decision(
                conn=conn,
                decision_id=decision["case_number"],
                raw_text=decision["text"],
                decision_date=decision.get("parsed", {}).get("decision_date"),
                extraction=extraction,
            )
            success_count += 1

        except Exception as e:
            logger.error(f"Failed to process {decision['case_number']}: {e}")
            continue

    conn.close()
    logger.info(f"Ingestion complete: {success_count}/{len(decisions)} succeeded")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-selection", action="store_true", help="Use existing selection")
    parser.add_argument("--limit", type=int, default=100, help="Max decisions to process")
    args = parser.parse_args()

    run_ingestion(skip_selection=args.skip_selection, limit=args.limit)
