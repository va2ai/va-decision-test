import pytest
from src.fetcher.search import search_bva, fetch_decision_text

def test_search_returns_results():
    """Search for PTSD cases, expect at least 1 result"""
    results = search_bva("PTSD service connection", year=2024, max_results=5)

    assert len(results) >= 1
    assert results[0]["url"].startswith("https://www.va.gov/")
    assert results[0]["case_number"] is not None

def test_fetch_decision_text():
    """Fetch a known decision and verify structure"""
    results = search_bva("tinnitus", year=2024, max_results=1)
    assert len(results) >= 1

    text = fetch_decision_text(results[0]["url"])
    assert len(text) > 1000
    assert "DECISION" in text.upper() or "ORDER" in text.upper()
