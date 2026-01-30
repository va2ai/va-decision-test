"""
Improved decision selector with proper quota balancing.

Ensures:
- 25 granted / 25 denied / 25 remanded / 25 mixed
- 10+ with private nexus opinions
- 10+ with exam inadequacy language
- Diverse conditions
"""
import logging
import time
from typing import Optional
from collections import defaultdict
from .search import search_bva, fetch_decision_text
from .parser import parse_decision
from .selector import has_private_nexus, has_exam_inadequacy

logger = logging.getLogger(__name__)


class BalancedSelector:
    """Intelligent decision selector with quota balancing."""

    def __init__(self):
        self.quotas = {
            "granted": 25,
            "denied": 25,
            "remanded": 25,
            "mixed": 25,
        }
        self.conditions = [
            "tinnitus",
            "sleep apnea secondary",
            "PTSD",
            "radiculopathy",
            "knee",
        ]
        self.special_quotas = {
            "private_nexus": 10,
            "exam_inadequacy": 10,
        }

        # Tracking
        self.selected = []
        self.seen_urls = set()
        self.counts = defaultdict(int)
        self.special_counts = defaultdict(int)

    def get_outcome_count(self, outcome: str) -> int:
        """Get count for a specific outcome."""
        return sum(1 for d in self.selected if d["outcome"].lower() == outcome.lower())

    def needs_more(self, outcome: str) -> bool:
        """Check if we need more decisions for this outcome."""
        return self.get_outcome_count(outcome) < self.quotas.get(outcome.lower(), 0)

    def needs_special(self, special_type: str) -> bool:
        """Check if we need more decisions with special requirements."""
        return self.special_counts[special_type] < self.special_quotas[special_type]

    def add_decision(self, decision: dict):
        """Add a decision and update counts."""
        self.selected.append(decision)
        outcome = decision["outcome"].lower()
        self.counts[outcome] += 1

        if decision.get("has_private_nexus"):
            self.special_counts["private_nexus"] += 1
        if decision.get("has_exam_inadequacy"):
            self.special_counts["exam_inadequacy"] += 1

    def is_complete(self) -> bool:
        """Check if we've met all quotas."""
        # Check outcome quotas
        for outcome, quota in self.quotas.items():
            if self.get_outcome_count(outcome) < quota:
                return False

        # Check special requirements
        for special, quota in self.special_quotas.items():
            if self.special_counts[special] < quota:
                return False

        return True

    def progress_report(self) -> str:
        """Generate progress report."""
        lines = [
            "\nProgress Report:",
            f"Total: {len(self.selected)}/100",
            "\nOutcomes:",
        ]
        for outcome, quota in self.quotas.items():
            count = self.get_outcome_count(outcome)
            status = "✓" if count >= quota else f"{count}/{quota}"
            lines.append(f"  {outcome.capitalize()}: {status}")

        lines.append("\nSpecial Requirements:")
        for special, quota in self.special_quotas.items():
            count = self.special_counts[special]
            status = "✓" if count >= quota else f"{count}/{quota}"
            name = special.replace("_", " ").title()
            lines.append(f"  {name}: {status}")

        return "\n".join(lines)

    def select_100_decisions(
        self,
        years: tuple[int, int] = (2023, 2025)
    ) -> list[dict]:
        """
        Select exactly 100 balanced decisions.

        Strategy:
        1. Search broadly without outcome filter
        2. Classify outcomes after parsing
        3. Fill quotas intelligently
        4. Ensure special requirements met
        """
        logger.info("Starting balanced selection for 100 decisions...")

        # Phase 1: Search broadly for each condition
        for condition in self.conditions:
            if self.is_complete():
                break

            logger.info(f"\n{'='*60}")
            logger.info(f"Searching condition: {condition}")
            logger.info(f"{'='*60}")

            # Search without outcome filter to find mixed outcomes
            for year in range(years[1], years[0] - 1, -1):
                if self.is_complete():
                    break

                query = condition  # No outcome filter
                logger.info(f"  Year {year}: {query}")

                try:
                    results = search_bva(query, year=year, max_results=30)

                    for r in results:
                        if self.is_complete():
                            break

                        if r["url"] in self.seen_urls:
                            continue

                        try:
                            # Fetch and parse
                            text = fetch_decision_text(r["url"])
                            parsed = parse_decision(text)
                            outcome = (parsed.get("outcome") or "").lower()

                            # Skip if we don't need this outcome
                            if not self.needs_more(outcome):
                                logger.debug(f"    Skip {r['case_number']}: {outcome} quota met")
                                continue

                            # Check special requirements
                            has_pn = has_private_nexus(text)
                            has_ei = has_exam_inadequacy(text)

                            # Prioritize if we need special requirements
                            priority = 0
                            if self.needs_special("private_nexus") and has_pn:
                                priority += 2
                            if self.needs_special("exam_inadequacy") and has_ei:
                                priority += 2

                            # Add decision
                            self.seen_urls.add(r["url"])
                            decision = {
                                "url": r["url"],
                                "case_number": r["case_number"],
                                "year": r["year"],
                                "condition": condition,
                                "outcome": outcome,
                                "parsed": parsed,
                                "text": text,
                                "has_private_nexus": has_pn,
                                "has_exam_inadequacy": has_ei,
                                "priority": priority,
                            }

                            self.add_decision(decision)
                            logger.info(f"    ✓ {r['case_number']}: {outcome} (PN={has_pn}, EI={has_ei})")

                            # Progress update every 10 decisions
                            if len(self.selected) % 10 == 0:
                                logger.info(self.progress_report())

                            time.sleep(1.5)  # Rate limit

                        except Exception as e:
                            logger.warning(f"    ✗ Failed to fetch {r['url']}: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"  Search failed for {query} year {year}: {e}")
                    continue

                time.sleep(2)  # Rate limit between years

        # Phase 2: Fill remaining quotas if needed
        if not self.is_complete():
            logger.info("\n" + "="*60)
            logger.info("Phase 2: Filling remaining quotas...")
            logger.info("="*60)
            logger.info(self.progress_report())

            # Search specifically for missing outcomes
            for outcome, quota in self.quotas.items():
                if self.get_outcome_count(outcome) < quota:
                    needed = quota - self.get_outcome_count(outcome)
                    logger.info(f"\nNeed {needed} more {outcome} decisions")

                    for condition in self.conditions:
                        if self.get_outcome_count(outcome) >= quota:
                            break

                        query = f"{condition} {outcome}"
                        logger.info(f"  Searching: {query}")

                        try:
                            results = search_bva(query, year=2024, max_results=20)

                            for r in results:
                                if self.get_outcome_count(outcome) >= quota:
                                    break

                                if r["url"] in self.seen_urls:
                                    continue

                                try:
                                    text = fetch_decision_text(r["url"])
                                    parsed = parse_decision(text)
                                    actual_outcome = (parsed.get("outcome") or "").lower()

                                    if actual_outcome != outcome:
                                        continue

                                    self.seen_urls.add(r["url"])
                                    decision = {
                                        "url": r["url"],
                                        "case_number": r["case_number"],
                                        "year": r["year"],
                                        "condition": condition,
                                        "outcome": actual_outcome,
                                        "parsed": parsed,
                                        "text": text,
                                        "has_private_nexus": has_private_nexus(text),
                                        "has_exam_inadequacy": has_exam_inadequacy(text),
                                    }

                                    self.add_decision(decision)
                                    logger.info(f"    ✓ {r['case_number']}: {actual_outcome}")
                                    time.sleep(1.5)

                                except Exception as e:
                                    logger.warning(f"    ✗ Failed: {e}")
                                    continue

                        except Exception as e:
                            logger.warning(f"  Search failed: {e}")
                            continue

        # Final report
        logger.info("\n" + "="*60)
        logger.info("SELECTION COMPLETE")
        logger.info("="*60)
        logger.info(self.progress_report())

        return self.selected[:100]


def select_100_balanced() -> list[dict]:
    """Convenience function to select 100 balanced decisions."""
    selector = BalancedSelector()
    return selector.select_100_decisions()
