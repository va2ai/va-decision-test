# tests/test_extraction.py
import pytest
import os
from src.extraction.models import ExtractionResult
from src.extraction.gemini import extract_entities

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)

SAMPLE_TEXT = """
Citation Nr: A24085357
Decision Date: December 19, 2024
DOCKET NO. 24-12345

ISSUE
Entitlement to service connection for tinnitus.

FINDING OF FACT
The Veteran has a current diagnosis of tinnitus, and the evidence establishes
that it is at least as likely as not related to in-service noise exposure.

The private physician, Dr. Smith, provided a nexus opinion stating the Veteran's
tinnitus is directly related to military service.

ORDER
Service connection for tinnitus is GRANTED.

Veterans Law Judge, John Doe
"""

def test_extract_entities_returns_valid_result():
    result = extract_entities(SAMPLE_TEXT)

    assert isinstance(result, ExtractionResult)
    assert len(result.issues) >= 1
    assert result.issues[0].condition is not None
    assert result.issues[0].outcome in ["Granted", "Denied", "Remanded", "Mixed"]

def test_extract_entities_finds_authorities():
    text_with_cfr = SAMPLE_TEXT + "\nPursuant to 38 C.F.R. § 3.303, service connection is warranted."
    result = extract_entities(text_with_cfr)

    assert len(result.authorities) >= 1
