import logging
import time
from typing import Optional
from .search import search_bva, fetch_decision_text
from .parser import parse_decision

logger = logging.getLogger(__name__)

SELECTION_CRITERIA = {
    "outcomes": {
        "granted": 25,
        "denied": 25,
        "remanded": 25,
        "mixed": 25,
    },
    "conditions": [
        "tinnitus",
        "sleep apnea secondary",
        "PTSD",
        "radiculopathy",
        "cancer",
    ],
    "special_requirements": {
        "private_nexus": 10,
        "exam_inadequacy": 10,
    },
}

def has_private_nexus(text: str) -> bool:
    """Check if decision contains private nexus language."""
    text_lower = text.lower()
    patterns = [
        "private medical opinion",
        "private physician",
        "independent medical",
        "ime ",
        "private nexus",
        "outside medical",
    ]
    return any(p in text_lower for p in patterns)

def has_exam_inadequacy(text: str) -> bool:
    """Check if decision contains exam inadequacy language."""
    text_lower = text.lower()
    patterns = [
        "inadequate examination",
        "inadequate for rating",
        "new examination",
        "another examination",
        "remand for.*examination",
        "examination is inadequate",
    ]
    return any(p in text_lower for p in patterns)

def select_decisions(
    max_per_bucket: int = 10,
    conditions: Optional[list[str]] = None,
    years: tuple[int, int] = (2022, 2025),
) -> list[dict]:
    """
    Select decisions meeting the criteria.

    Args:
        max_per_bucket: Max decisions per (condition, outcome) bucket
        conditions: List of conditions to search (defaults to SELECTION_CRITERIA)
        years: Year range to search

    Returns:
        List of decision dicts with url, case_number, outcome, condition, text
    """
    if conditions is None:
        conditions = SELECTION_CRITERIA["conditions"]

    selected = []
    seen_urls = set()

    for condition in conditions:
        for outcome in ["granted", "denied", "remanded"]:
            query = f"{condition} {outcome}"
            logger.info(f"Searching: {query}")

            for year in range(years[1], years[0] - 1, -1):
                if len([s for s in selected if s["condition"] == condition and s["outcome"] == outcome]) >= max_per_bucket:
                    break

                try:
                    results = search_bva(query, year=year, max_results=max_per_bucket * 2)

                    for r in results:
                        if r["url"] in seen_urls:
                            continue

                        if len([s for s in selected if s["condition"] == condition and s["outcome"] == outcome]) >= max_per_bucket:
                            break

                        try:
                            text = fetch_decision_text(r["url"])
                            parsed = parse_decision(text)

                            # Verify outcome matches
                            actual_outcome = (parsed.get("outcome") or "").lower()
                            if actual_outcome != outcome and outcome != "mixed":
                                continue

                            seen_urls.add(r["url"])
                            selected.append({
                                "url": r["url"],
                                "case_number": r["case_number"],
                                "year": r["year"],
                                "condition": condition,
                                "outcome": actual_outcome or outcome,
                                "parsed": parsed,
                                "text": text,
                                "has_private_nexus": has_private_nexus(text),
                                "has_exam_inadequacy": has_exam_inadequacy(text),
                            })

                            logger.info(f"Selected: {r['case_number']} ({condition}, {outcome})")
                            time.sleep(1)  # Rate limit

                        except Exception as e:
                            logger.warning(f"Failed to fetch {r['url']}: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Search failed for {query} year {year}: {e}")
                    continue

    return selected

def select_100_decisions() -> list[dict]:
    """Select exactly 100 decisions meeting all criteria."""
    # First pass: get candidates
    candidates = select_decisions(max_per_bucket=8)

    # TODO: Implement quota balancing for 25/25/25/25 and special requirements
    # For now, return what we have
    return candidates[:100]
