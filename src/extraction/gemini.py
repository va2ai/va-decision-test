import os
import json
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .models import ExtractionResult, ExtractedIssue, ExtractedPassage

load_dotenv()
logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
Analyze this BVA decision and extract structured data.

Return JSON with this exact schema:
{
  "issues": [
    {
      "issue_text": "Entitlement to service connection for...",
      "outcome": "Granted|Denied|Remanded|Mixed",
      "connection_type": "Direct|Secondary|Aggravation|null",
      "condition": "normalized condition name",
      "evidence_types": ["STR", "VA_EXAM", "PRIVATE_OPINION", "LAY_EVIDENCE"],
      "provider_types": ["VA_EXAMINER", "PRIVATE_IME", "TREATING_PHYSICIAN"]
    }
  ],
  "authorities": ["38 C.F.R. § 3.310", "Gilbert v. Derwinski"],
  "passages": [
    {
      "text": "The private physician opined that...",
      "tag": "MEDICAL_OPINION|EXAM_ADEQUACY|LAY_EVIDENCE|REASONS_BASES",
      "confidence": 0.85
    }
  ],
  "system_type": "AMA|Legacy|null"
}

Only extract what is explicitly stated. Set confidence lower (0.6-0.7)
for inferred relationships, higher (0.9-1.0) for explicit ones.

Limit to 5 most important passages. Keep passage text under 500 chars.

DECISION TEXT:
"""

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)

def extract_entities(text: str, max_text_length: int = 30000) -> ExtractionResult:
    """Extract entities from BVA decision text using Gemini Flash."""
    client = get_client()

    # Truncate if too long
    if len(text) > max_text_length:
        text = text[:max_text_length]

    prompt = EXTRACTION_PROMPT + text

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        logger.debug(f"Response text: {response.text[:500]}")
        return ExtractionResult()

    # Parse into Pydantic models
    issues = [ExtractedIssue(**i) for i in data.get("issues", [])]
    passages = [ExtractedPassage(**p) for p in data.get("passages", [])]

    return ExtractionResult(
        issues=issues,
        authorities=data.get("authorities", []),
        passages=passages,
        system_type=data.get("system_type"),
    )
