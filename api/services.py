"""
Service layer for FastAPI endpoints.

Implements business logic for:
- Search and fetch
- Parsing
- LLM extraction
- Database queries
- Ingestion pipeline
"""
import logging
from typing import Optional, Literal
from src.fetcher.search import search_bva, fetch_decision_text
from src.fetcher.parser import parse_decision
from src.extraction.gemini import extract_entities
from src.db.connection import get_connection
from src.queries.q1_similar import find_similar_cases
from src.queries.q2_evidence_chain import get_evidence_chain
from src.queries.q3_denial_why import analyze_denial
from src.queries.q4_evidence_diff import compare_evidence_by_outcome
from src.queries.q5_authority_stats import get_authority_stats
from src.graph.loader import load_decision
from api.models import (
    DecisionMetadata,
    DecisionResponse,
    ExtractionResponse,
    IssueExtraction,
    PassageData,
    SimilarCase,
    EvidenceChainResponse,
    DenialAnalysisResponse,
    EvidenceDiffItem,
    AuthorityStatsItem,
    IngestResponse,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SEARCH & FETCH SERVICES
# ============================================================================

def search_decisions(
    query: str,
    year: Optional[int] = None,
    max_results: int = 20,
    max_pages: int = 1
) -> list[DecisionMetadata]:
    """
    Search BVA decisions via USA.gov search.

    Args:
        query: Search query string
        year: Optional year filter
        max_results: Max results to return
        max_pages: Max pages to fetch

    Returns:
        List of decision metadata
    """
    results = search_bva(
        query=query,
        year=year,
        max_results=max_results,
        max_pages=max_pages
    )

    return [DecisionMetadata(**r) for r in results]


def fetch_and_parse_decision(
    case_number: str,
    year: Optional[int] = None
) -> DecisionResponse:
    """
    Fetch a decision by case number and year.

    Args:
        case_number: Case number (e.g., 'A24084938')
        year: Year of decision (e.g., 2024)

    Returns:
        DecisionResponse with raw text and parsed metadata

    Raises:
        ValueError: If decision not found
    """
    # Construct URL
    if not year:
        raise ValueError("Year is required when fetching by case number")

    yy = str(year)[2:]  # 2024 → "24"
    url = f"https://www.va.gov/vetapp{yy}/Files12/{case_number}.txt"

    # Fetch text
    try:
        raw_text = fetch_decision_text(url)
    except Exception as e:
        raise ValueError(f"Decision not found at {url}: {e}")

    # Parse
    parsed = parse_decision(raw_text)

    return DecisionResponse(
        case_number=case_number,
        url=url,
        year=year,
        raw_text=raw_text,
        text_length=len(raw_text),
        parsed=parsed
    )


# ============================================================================
# EXTRACTION SERVICES
# ============================================================================

def extract_decision_entities(text: str) -> ExtractionResponse:
    """
    Extract structured entities from decision text using LLM.

    Args:
        text: Raw decision text

    Returns:
        ExtractionResponse with extracted issues and entities
    """
    extraction = extract_entities(text)

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


# ============================================================================
# QUERY SERVICES
# ============================================================================

def find_similar_cases_service(
    query_text: str,
    limit: int = 5,
    outcome_filter: Optional[str] = None
) -> list[SimilarCase]:
    """
    Find similar cases using vector similarity.

    Args:
        query_text: Text to search for
        limit: Max results
        outcome_filter: Optional outcome filter

    Returns:
        List of similar cases
    """
    conn = get_connection()
    try:
        results = find_similar_cases(
            conn=conn,
            query_text=query_text,
            limit=limit,
            outcome_filter=outcome_filter
        )
        return [SimilarCase(**r) for r in results]
    finally:
        conn.close()


def get_evidence_chain_service(issue_id: int) -> EvidenceChainResponse:
    """
    Get complete evidence chain for an issue.

    Args:
        issue_id: Issue ID

    Returns:
        Evidence chain data
    """
    conn = get_connection()
    try:
        chain = get_evidence_chain(conn=conn, issue_id=issue_id)
        return EvidenceChainResponse(**chain)
    finally:
        conn.close()


def analyze_denial_service(issue_id: int) -> DenialAnalysisResponse:
    """
    Analyze why an issue was denied.

    Args:
        issue_id: Issue ID

    Returns:
        Denial analysis data
    """
    conn = get_connection()
    try:
        analysis = analyze_denial(conn=conn, issue_id=issue_id)
        return DenialAnalysisResponse(**analysis)
    finally:
        conn.close()


def compare_evidence_service(condition: str) -> list[EvidenceDiffItem]:
    """
    Compare evidence patterns by outcome.

    Args:
        condition: Condition name

    Returns:
        Evidence frequency by outcome
    """
    conn = get_connection()
    try:
        results = compare_evidence_by_outcome(conn=conn, condition=condition)
        return [EvidenceDiffItem(**r) for r in results]
    finally:
        conn.close()


def get_authority_stats_service(condition: Optional[str] = None) -> list[AuthorityStatsItem]:
    """
    Get authority citation statistics.

    Args:
        condition: Optional condition filter

    Returns:
        Authority citation frequency by outcome
    """
    conn = get_connection()
    try:
        results = get_authority_stats(conn=conn, condition=condition)
        return [AuthorityStatsItem(**r) for r in results]
    finally:
        conn.close()


# ============================================================================
# INGESTION SERVICES
# ============================================================================

def ingest_decision_service(
    case_number: Optional[str] = None,
    year: Optional[int] = None,
    url: Optional[str] = None
) -> IngestResponse:
    """
    Full ingestion pipeline: fetch → parse → extract → load.

    Args:
        case_number: Case number
        year: Year of decision
        url: Direct URL (optional, overrides case_number/year)

    Returns:
        IngestResponse with success status
    """
    # Fetch decision
    if url:
        raw_text = fetch_decision_text(url)
        # Extract case number from URL
        case_number = url.split("/")[-1].replace(".txt", "")
    elif case_number and year:
        decision = fetch_and_parse_decision(case_number, year)
        raw_text = decision.raw_text
        url = decision.url
    else:
        raise ValueError("Either url or (case_number + year) required")

    # Parse
    parsed = parse_decision(raw_text)

    # Extract entities
    extraction = extract_entities(raw_text)

    # Load to database
    conn = get_connection()
    try:
        load_decision(
            conn=conn,
            decision_id=case_number,
            raw_text=raw_text,
            decision_date=parsed.get("decision_date"),
            extraction=extraction
        )
        conn.commit()

        issues_extracted = len(extraction.issues)

        return IngestResponse(
            success=True,
            case_number=case_number,
            message=f"Successfully ingested decision {case_number}",
            issues_extracted=issues_extracted,
            issues_loaded=issues_extracted
        )
    except Exception as e:
        conn.rollback()
        logger.error(f"Ingestion failed for {case_number}: {e}")
        raise
    finally:
        conn.close()
