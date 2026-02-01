import pytest
from src.fetcher.search import search_bva, fetch_decision_text
from src.fetcher.parser import parse_decision

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

def test_parse_decision_extracts_metadata():
    """Parse a decision and verify extracted fields"""
    results = search_bva("granted service connection", year=2024, max_results=1)
    text = fetch_decision_text(results[0]["url"])

    parsed = parse_decision(text)

    # Should have at least some fields populated
    assert "decision_date" in parsed
    assert "outcome" in parsed
    assert "issues" in parsed
    assert isinstance(parsed["issues"], list)
