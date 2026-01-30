"""
Pydantic models for FastAPI request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


# ============================================================================
# SEARCH & FETCH MODELS
# ============================================================================

class SearchRequest(BaseModel):
    """Request model for BVA decision search."""
    query: str = Field(..., description="Search query (e.g., 'tinnitus granted')")
    year: Optional[int] = Field(None, description="Filter by year (2020-2025)")
    max_results: int = Field(20, ge=1, le=100, description="Max results to return")
    max_pages: int = Field(1, ge=1, le=10, description="Max pages to fetch")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "tinnitus granted",
                "year": 2024,
                "max_results": 10,
                "max_pages": 1
            }
        }


class DecisionMetadata(BaseModel):
    """Metadata for a single decision from search results."""
    url: str
    case_number: str
    title: str
    snippet: str
    year: int


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: list[DecisionMetadata]
    count: int


class DecisionResponse(BaseModel):
    """Response model for a fetched decision."""
    case_number: str
    url: str
    year: int
    raw_text: str
    text_length: int
    parsed: Optional[dict] = None


class ParsedDecisionResponse(BaseModel):
    """Response model for parsed decision metadata."""
    decision_date: Optional[str]
    docket_no: Optional[str]
    outcome: Optional[Literal["Granted", "Denied", "Remanded", "Mixed"]]
    issues: list[str]
    citations: list[str]
    regional_office: Optional[str]
    judge: Optional[str]
    system_type: Optional[Literal["AMA", "Legacy"]]


# ============================================================================
# EXTRACTION MODELS
# ============================================================================

class PassageData(BaseModel):
    """Key passage from decision."""
    text: str
    tag: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class IssueExtraction(BaseModel):
    """Extracted issue with entities."""
    issue_text: str
    condition: str
    outcome: str
    evidence_types: list[str]
    provider_types: list[str]
    authorities: list[str]
    key_passages: list[PassageData]


class ExtractionResponse(BaseModel):
    """Response model for LLM entity extraction."""
    issues: list[IssueExtraction]
    extraction_model: str = "gemini-2.0-flash"


# ============================================================================
# QUERY MODELS (MVP Validation)
# ============================================================================

class SimilarCasesRequest(BaseModel):
    """Request for similar cases query."""
    query_text: str = Field(..., description="Text to find similar cases for")
    limit: int = Field(5, ge=1, le=20, description="Max results to return")
    outcome_filter: Optional[Literal["Granted", "Denied", "Remanded", "Mixed"]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "tinnitus noise exposure",
                "limit": 5,
                "outcome_filter": "Granted"
            }
        }


class SimilarCase(BaseModel):
    """Single similar case result."""
    passage: str
    issue_text: str
    outcome: str
    condition: Optional[str]
    decision_id: str
    similarity: Optional[float] = None


class SimilarCasesResponse(BaseModel):
    """Response for similar cases query."""
    results: list[SimilarCase]
    count: int


class EvidenceChainResponse(BaseModel):
    """Response for evidence chain query."""
    issue_id: int
    condition: Optional[str]
    outcome: Optional[str]
    evidence_types: list[str]
    provider_types: list[str]
    authorities: list[str]
    passages: list[str]


class DenialAnalysisResponse(BaseModel):
    """Response for denial analysis query."""
    issue_id: int
    outcome: Optional[str]
    missing_evidence: list[str]
    present_evidence: list[str]
    exam_passages: list[str]


class EvidenceDiffItem(BaseModel):
    """Evidence type frequency by outcome."""
    evidence_type: str
    outcome: str
    count: int


class EvidenceDiffResponse(BaseModel):
    """Response for evidence diff query."""
    results: list[EvidenceDiffItem]
    count: int


class AuthorityStatsItem(BaseModel):
    """Authority citation frequency by outcome."""
    citation: str
    outcome: str
    count: int


class AuthorityStatsResponse(BaseModel):
    """Response for authority stats query."""
    results: list[AuthorityStatsItem]
    count: int


# ============================================================================
# INGESTION MODELS
# ============================================================================

class IngestRequest(BaseModel):
    """Request for full ingestion pipeline."""
    case_number: Optional[str] = Field(None, description="Case number (e.g., 'A24084938')")
    year: Optional[int] = Field(None, description="Year of decision")
    url: Optional[str] = Field(None, description="Direct URL to decision")

    class Config:
        json_schema_extra = {
            "example": {
                "case_number": "A24084938",
                "year": 2024
            }
        }


class IngestResponse(BaseModel):
    """Response for ingestion pipeline."""
    success: bool
    case_number: str
    message: str
    issues_extracted: int
    issues_loaded: int
