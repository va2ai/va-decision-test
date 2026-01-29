# tests/test_selector.py
import pytest
from src.fetcher.selector import select_decisions, SELECTION_CRITERIA

def test_selection_criteria_defined():
    """Verify selection criteria are properly defined"""
    assert SELECTION_CRITERIA["outcomes"]["granted"] == 25
    assert SELECTION_CRITERIA["outcomes"]["denied"] == 25
    assert SELECTION_CRITERIA["outcomes"]["remanded"] == 25
    assert SELECTION_CRITERIA["outcomes"]["mixed"] == 25
    assert len(SELECTION_CRITERIA["conditions"]) >= 3

def test_select_decisions_returns_candidates():
    """Select a small batch to verify the selector works"""
    # Use small numbers for testing
    decisions = select_decisions(max_per_bucket=2, conditions=["PTSD"])

    assert len(decisions) > 0
    assert all("url" in d for d in decisions)
    assert all("outcome" in d for d in decisions)
