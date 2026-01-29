# tests/test_queries.py
import pytest
import os
from src.db.connection import get_connection, init_schema
from src.queries.q1_similar import find_similar_cases

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
