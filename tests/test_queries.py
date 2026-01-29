# tests/test_queries.py
import pytest
import os
from src.db.connection import get_connection, init_schema
from src.queries.q1_similar import find_similar_cases
from src.queries.q2_evidence_chain import get_evidence_chain
from src.queries.q3_denial_why import analyze_denial
from src.queries.q4_evidence_diff import compare_evidence_by_outcome
from src.queries.q5_authority_stats import get_authority_stats

# Skip if no database available
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_DB_TESTS", "false").lower() == "true",
    reason="Database not available"
)

@pytest.fixture
def db_conn():
    try:
        conn = get_connection()
        init_schema(conn)
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

def test_find_similar_returns_results(db_conn):
    """Test similarity search returns expected structure"""
    # This will return empty until we have data with embeddings
    results = find_similar_cases(db_conn, "tinnitus service connection noise exposure", limit=5)

    assert isinstance(results, list)
    # Each result should have expected keys when populated
    # For now just verify the function runs without error

def test_evidence_chain_returns_structure(db_conn):
    result = get_evidence_chain(db_conn, issue_id=1)
    assert "condition" in result
    assert "evidence_types" in result
    assert "authorities" in result

def test_denial_analysis_returns_structure(db_conn):
    result = analyze_denial(db_conn, issue_id=1)
    assert "missing_evidence" in result
    assert "exam_passages" in result

def test_evidence_diff_returns_structure(db_conn):
    results = compare_evidence_by_outcome(db_conn, condition="tinnitus")
    assert isinstance(results, list)

def test_authority_stats_returns_structure(db_conn):
    results = get_authority_stats(db_conn, condition="tinnitus")
    assert isinstance(results, list)
