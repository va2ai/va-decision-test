#!/usr/bin/env python3
"""
FastAPI application for BVA decision analysis.

Provides REST endpoints for:
- Searching BVA decisions
- Fetching and parsing decisions
- LLM entity extraction
- Graph-based similarity queries
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from typing import Optional, Literal
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from api.models import (
    SearchRequest,
    SearchResponse,
    DecisionResponse,
    ParsedDecisionResponse,
    ExtractionResponse,
    SimilarCasesRequest,
    SimilarCasesResponse,
    EvidenceChainResponse,
    DenialAnalysisResponse,
    EvidenceDiffResponse,
    AuthorityStatsResponse,
    IngestRequest,
    IngestResponse,
)
from api.services import (
    search_decisions,
    fetch_and_parse_decision,
    extract_decision_entities,
    find_similar_cases_service,
    get_evidence_chain_service,
    analyze_denial_service,
    compare_evidence_service,
    get_authority_stats_service,
    ingest_decision_service,
)
from api.middleware import ObservabilityMiddleware
from api.observability import metrics, StructuredLogger

# Configure structured logging
logger = StructuredLogger("api.main")

# Create FastAPI app
app = FastAPI(
    title="VA Decision Analysis API",
    description="""
    Production-ready API for analyzing Board of Veterans' Appeals (BVA) decisions.

    ## Features

    - **Search**: Query BVA decisions via USA.gov search
    - **Parse**: Extract structured metadata from decision text
    - **Extract**: LLM-powered entity extraction (Gemini 2.0 Flash)
    - **Query**: Graph-based similarity and evidence analysis
    - **Ingest**: Full pipeline from search to database

    ## Use Cases

    - Legal research and precedent discovery
    - Evidence pattern analysis
    - Citation frequency analysis
    - Decision support systems
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add observability middleware (before CORS)
app.add_middleware(ObservabilityMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "va-decision-api"}

# Metrics endpoint
@app.get("/metrics", tags=["Health"])
async def get_metrics():
    """
    Get application metrics summary.

    **Returns:** Latency, token usage, and error statistics.
    """
    return metrics.get_summary()

# Dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse, tags=["Health"], include_in_schema=True)
async def get_dashboard():
    """
    Developer dashboard with real-time metrics and logs.

    **Features:**
    - Real-time metrics visualization
    - Latency charts
    - Error categorization
    - Recent activity logs
    - API endpoint statistics
    """
    import os
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    logger.info(f"Loading dashboard from: {dashboard_path}")

    if not os.path.exists(dashboard_path):
        logger.error(f"Dashboard file not found at: {dashboard_path}")
        raise HTTPException(status_code=404, detail=f"Dashboard not found at {dashboard_path}")

    with open(dashboard_path, 'r', encoding='utf-8') as f:
        content = f.read()
        logger.info("Dashboard loaded successfully")
        return HTMLResponse(content=content)

# Logs endpoint
@app.get("/logs", tags=["Health"])
async def get_logs(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent log entries.

    **Parameters:**
    - limit: Maximum number of log entries to return (1-100)

    **Returns:** List of recent log entries with metadata.
    """
    # In production, this would read from a log buffer or file
    # For now, return a simple structure
    return {
        "logs": [],
        "count": 0,
        "message": "Log streaming not yet implemented - check server console for logs"
    }

# ============================================================================
# SEARCH & FETCH ENDPOINTS
# ============================================================================

@app.post("/api/v1/search", response_model=SearchResponse, tags=["Search & Fetch"])
async def search(request: SearchRequest):
    """
    Search BVA decisions via USA.gov search.

    **Example:**
    ```json
    {
      "query": "tinnitus granted",
      "year": 2024,
      "max_results": 10
    }
    ```

    **Returns:** List of decision metadata with URLs.
    """
    try:
        results = search_decisions(
            query=request.query,
            year=request.year,
            max_results=request.max_results,
            max_pages=request.max_pages
        )
        return SearchResponse(results=results, count=len(results))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/v1/decision/{case_number}", response_model=DecisionResponse, tags=["Search & Fetch"])
async def get_decision(
    case_number: str,
    year: Optional[int] = Query(None, description="Year of decision (e.g., 2024)")
):
    """
    Fetch a specific decision by case number.

    **Example:** `/api/v1/decision/A24084938?year=2024`

    **Returns:** Raw decision text and metadata.
    """
    try:
        decision = fetch_and_parse_decision(case_number, year)
        return decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch decision {case_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")


@app.post("/api/v1/parse", response_model=ParsedDecisionResponse, tags=["Search & Fetch"])
async def parse_decision_text(text: str):
    """
    Parse decision text to extract structured metadata.

    **Extracts:**
    - Decision date
    - Docket number
    - Outcome (Granted/Denied/Remanded/Mixed)
    - Issues
    - Citations (38 CFR)
    - Judge name
    - Regional office
    """
    from src.fetcher.parser import parse_decision
    try:
        parsed = parse_decision(text)
        return ParsedDecisionResponse(**parsed)
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


# ============================================================================
# EXTRACTION ENDPOINTS
# ============================================================================

@app.post("/api/v1/extract", response_model=ExtractionResponse, tags=["Extraction"])
async def extract_entities(text: str, background_tasks: BackgroundTasks):
    """
    Extract structured entities from decision text using LLM (Gemini 2.0 Flash).

    **Extracts:**
    - Issues with conditions and outcomes
    - Evidence types (STR, VA_EXAM, PRIVATE_OPINION, LAY_EVIDENCE)
    - Provider types (VA_EXAMINER, PRIVATE_IME, TREATING_PHYSICIAN)
    - Legal authorities (38 CFR, case law)
    - Key passages with confidence scores

    **Note:** This endpoint may take 5-10 seconds due to LLM processing.
    """
    try:
        extraction = extract_decision_entities(text)
        return extraction
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# ============================================================================
# QUERY ENDPOINTS (MVP Validation)
# ============================================================================

@app.post("/api/v1/query/similar", response_model=SimilarCasesResponse, tags=["Queries"])
async def query_similar_cases(request: SimilarCasesRequest):
    """
    Find similar cases using vector similarity search.

    **Query 1 from MVP validation.**

    **Example:**
    ```json
    {
      "query_text": "tinnitus noise exposure",
      "limit": 5,
      "outcome_filter": "Granted"
    }
    ```

    **Returns:** Top N similar passages with issue outcomes and conditions.
    """
    try:
        results = find_similar_cases_service(
            query_text=request.query_text,
            limit=request.limit,
            outcome_filter=request.outcome_filter
        )
        return SimilarCasesResponse(results=results, count=len(results))
    except Exception as e:
        logger.error(f"Similar cases query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/v1/query/evidence-chain/{issue_id}", response_model=EvidenceChainResponse, tags=["Queries"])
async def query_evidence_chain(issue_id: int):
    """
    Get complete evidence chain for an issue.

    **Query 2 from MVP validation.**

    **Returns:**
    - Condition
    - Evidence types
    - Provider types
    - Authorities cited
    - Key passages
    """
    try:
        chain = get_evidence_chain_service(issue_id)
        return chain
    except Exception as e:
        logger.error(f"Evidence chain query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/v1/query/denial-analysis/{issue_id}", response_model=DenialAnalysisResponse, tags=["Queries"])
async def query_denial_analysis(issue_id: int):
    """
    Analyze why an issue was denied.

    **Query 3 from MVP validation.**

    **Returns:**
    - Missing evidence types
    - Present evidence types
    - Exam adequacy passages
    """
    try:
        analysis = analyze_denial_service(issue_id)
        return analysis
    except Exception as e:
        logger.error(f"Denial analysis query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/v1/query/evidence-diff", response_model=EvidenceDiffResponse, tags=["Queries"])
async def query_evidence_diff(
    condition: str = Query(..., description="Condition name (e.g., 'tinnitus')")
):
    """
    Compare evidence patterns between outcomes.

    **Query 4 from MVP validation.**

    **Example:** `/api/v1/query/evidence-diff?condition=tinnitus`

    **Returns:** Evidence type frequency by outcome (granted vs denied).
    """
    try:
        diff = compare_evidence_service(condition)
        return EvidenceDiffResponse(results=diff, count=len(diff))
    except Exception as e:
        logger.error(f"Evidence diff query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/v1/query/authority-stats", response_model=AuthorityStatsResponse, tags=["Queries"])
async def query_authority_stats(
    condition: Optional[str] = Query(None, description="Filter by condition")
):
    """
    Get authority citation statistics by outcome.

    **Query 5 from MVP validation.**

    **Example:** `/api/v1/query/authority-stats?condition=tinnitus`

    **Returns:** Authority citation frequency by outcome.
    """
    try:
        stats = get_authority_stats_service(condition)
        return AuthorityStatsResponse(results=stats, count=len(stats))
    except Exception as e:
        logger.error(f"Authority stats query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ============================================================================
# INGESTION ENDPOINTS
# ============================================================================

@app.post("/api/v1/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_decision(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Full ingestion pipeline: fetch → parse → extract → load to database.

    **Example:**
    ```json
    {
      "case_number": "A24084938",
      "year": 2024
    }
    ```

    **Note:** This is a long-running operation (10-15 seconds).
    For production, consider using background tasks or a job queue.
    """
    try:
        result = ingest_decision_service(
            case_number=request.case_number,
            year=request.year,
            url=request.url
        )
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
