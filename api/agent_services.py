#!/usr/bin/env python3
"""
Agent-wrapped service layer demonstrating runtime integration.

Shows how to use AgentRuntime for:
- Input validation
- Tool-call tracing
- Confidence scoring
- Retry logic
"""
from typing import Optional
from src.extraction.gemini import extract_entities
from src.fetcher.search import search_bva, fetch_decision_text
from src.fetcher.parser import parse_decision
from api.agent_runtime import (
    AgentRuntime,
    AgentResult,
    agent_wrapper,
    text_length_confidence,
    extraction_confidence,
)
from api.models import ExtractionResponse, IssueExtraction, PassageData
from api.observability import StructuredLogger

logger = StructuredLogger("agent.services")


# ============================================================================
# EXTRACTION AGENT
# ============================================================================

def validate_extraction_input(args: tuple) -> bool:
    """Validate extraction input."""
    if not args or len(args) == 0:
        return False
    text = args[0]
    if not isinstance(text, str):
        return False
    if len(text) < 100:  # Minimum viable decision length
        return False
    return True


def fallback_extraction(text: str) -> ExtractionResponse:
    """Fallback when LLM extraction fails."""
    logger.warning("Using fallback extraction (empty response)")
    return ExtractionResponse(issues=[])


# Wrapped extraction function
extraction_runtime = AgentRuntime(
    agent_name="entity_extraction",
    max_retries=2,
    retry_delay=2.0,
    fallback_fn=fallback_extraction,
)


def extract_with_runtime(text: str) -> AgentResult[ExtractionResponse]:
    """
    Extract entities with full runtime support.

    Returns:
        AgentResult with extraction data, trace, and confidence
    """
    def _extract_internal(text: str) -> ExtractionResponse:
        """Internal extraction with tool tracing."""
        # Create a trace for this execution
        from api.agent_runtime import AgentTrace
        trace = AgentTrace(agent_name="entity_extraction", start_time=0)

        # Trace the LLM call
        with extraction_runtime.trace_tool_call("gemini_api", trace):
            extraction = extract_entities(text)

        # Convert to response model
        issues = []
        for issue in extraction.issues:
            passages = [
                PassageData(
                    text=p.text,
                    tag=p.tag,
                    confidence=p.confidence
                ) for p in issue.passages
            ]

            issues.append(IssueExtraction(
                issue_text=issue.issue_text,
                condition=issue.condition,
                outcome=issue.outcome,
                evidence_types=issue.evidence_types,
                provider_types=issue.provider_types,
                authorities=issue.authorities,
                key_passages=passages
            ))

        return ExtractionResponse(issues=issues)

    # Execute with runtime
    return extraction_runtime.execute(
        _extract_internal,
        text,
        validate_input=validate_extraction_input,
        calculate_confidence=extraction_confidence,
    )


# ============================================================================
# FETCH AGENT
# ============================================================================

def validate_fetch_input(args: tuple) -> bool:
    """Validate fetch input."""
    if not args or len(args) < 1:
        return False
    url = args[0]
    if not isinstance(url, str):
        return False
    if not url.startswith("http"):
        return False
    return True


def fallback_fetch(url: str) -> str:
    """Fallback when fetch fails."""
    logger.warning(f"Fetch failed for {url}, returning empty")
    return ""


fetch_runtime = AgentRuntime(
    agent_name="decision_fetch",
    max_retries=3,
    retry_delay=1.0,
    fallback_fn=fallback_fetch,
)


def fetch_with_runtime(url: str) -> AgentResult[str]:
    """
    Fetch decision with runtime support.

    Returns:
        AgentResult with decision text, trace, and confidence
    """
    def _fetch_internal(url: str) -> str:
        from api.agent_runtime import AgentTrace
        trace = AgentTrace(agent_name="decision_fetch", start_time=0)

        with fetch_runtime.trace_tool_call("http_fetch", trace):
            text = fetch_decision_text(url)

        return text

    return fetch_runtime.execute(
        _fetch_internal,
        url,
        validate_input=validate_fetch_input,
        calculate_confidence=lambda text: text_length_confidence(text, min_length=500),
    )


# ============================================================================
# SEARCH AGENT
# ============================================================================

def validate_search_input(args: tuple) -> bool:
    """Validate search input."""
    if not args or len(args) == 0:
        return False
    query = args[0]
    if not isinstance(query, str):
        return False
    if len(query) < 3:  # Minimum query length
        return False
    return True


search_runtime = AgentRuntime(
    agent_name="decision_search",
    max_retries=2,
    retry_delay=1.5,
)


def search_with_runtime(
    query: str,
    year: Optional[int] = None,
    max_results: int = 20
) -> AgentResult[list[dict]]:
    """
    Search decisions with runtime support.

    Returns:
        AgentResult with search results, trace, and confidence
    """
    def _search_internal(query: str, year: Optional[int], max_results: int) -> list[dict]:
        from api.agent_runtime import AgentTrace
        trace = AgentTrace(agent_name="decision_search", start_time=0)

        with search_runtime.trace_tool_call("usa_gov_search", trace):
            results = search_bva(query=query, year=year, max_results=max_results)

        return results

    return search_runtime.execute(
        _search_internal,
        query,
        year,
        max_results,
        validate_input=validate_search_input,
        calculate_confidence=lambda results: min(1.0, len(results) / 10),
    )


# ============================================================================
# DECORATOR EXAMPLE
# ============================================================================

@agent_wrapper("decision_parser", max_retries=1)
def parse_with_runtime(text: str) -> dict:
    """
    Parse decision with decorator-based runtime.

    Returns:
        AgentResult with parsed data
    """
    parsed = parse_decision(text)
    return parsed


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_extraction():
    """Example: Extract entities with full observability."""
    sample_text = "Sample BVA decision text..." * 100

    result = extract_with_runtime(sample_text)

    if result.success:
        print(f"✓ Extraction succeeded")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Duration: {result.trace.duration_ms:.0f}ms")
        print(f"  Issues found: {len(result.data.issues)}")
        print(f"  Tool calls: {len(result.trace.tool_calls)}")
    else:
        print(f"✗ Extraction failed: {result.trace.error}")
        print(f"  Retries: {result.trace.retries}")


def example_fetch():
    """Example: Fetch decision with retry logic."""
    url = "https://www.va.gov/vetapp24/Files12/A24084938.txt"

    result = fetch_with_runtime(url)

    if result.success:
        print(f"✓ Fetch succeeded")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Text length: {len(result.data)}")
    else:
        print(f"✗ Fetch failed: {result.trace.error}")


def example_search():
    """Example: Search with input validation."""
    result = search_with_runtime("tinnitus granted", year=2024, max_results=5)

    if result.success:
        print(f"✓ Search succeeded")
        print(f"  Results: {len(result.data)}")
        print(f"  Confidence: {result.confidence:.2f}")

        # Show tool call details
        for call in result.trace.tool_calls:
            print(f"  Tool: {call.tool_name} ({call.duration_ms:.0f}ms)")
    else:
        print(f"✗ Search failed")


if __name__ == "__main__":
    print("Agent Runtime Examples\n")

    print("1. Extraction Agent:")
    example_extraction()

    print("\n2. Fetch Agent:")
    example_fetch()

    print("\n3. Search Agent:")
    example_search()
