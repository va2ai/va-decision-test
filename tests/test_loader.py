# tests/test_loader.py
import pytest
import os
from src.db.connection import get_connection, init_schema
from src.graph.loader import load_decision
from src.extraction.models import ExtractionResult, ExtractedIssue, ExtractedPassage

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
        # Cleanup
        conn.execute("DELETE FROM decisions WHERE decision_id LIKE 'TEST%'")
        conn.commit()
        conn.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

def test_load_decision_creates_nodes(db_conn):
    extraction = ExtractionResult(
        issues=[
            ExtractedIssue(
                issue_text="Entitlement to service connection for tinnitus",
                outcome="Granted",
                condition="tinnitus",
                evidence_types=["VA_EXAM", "LAY_EVIDENCE"],
                provider_types=["VA_EXAMINER"],
            )
        ],
        authorities=["38 C.F.R. § 3.303"],
        passages=[
            ExtractedPassage(
                text="The examiner found...",
                tag="MEDICAL_OPINION",
                confidence=0.9,
            )
        ],
        system_type="AMA",
    )

    decision_id = load_decision(
        conn=db_conn,
        decision_id="TEST001",
        raw_text="Full decision text here...",
        decision_date="2024-12-19",
        extraction=extraction,
    )

    assert decision_id is not None

    # Verify decision was created
    cur = db_conn.execute("SELECT id FROM decisions WHERE decision_id = 'TEST001'")
    assert cur.fetchone() is not None

    # Verify issue was created
    cur = db_conn.execute("SELECT outcome FROM issues WHERE decision_id = %s", (decision_id,))
    row = cur.fetchone()
    assert row[0] == "Granted"

    # Verify condition was created and linked
    cur = db_conn.execute("""
        SELECT c.name FROM conditions c
        JOIN issue_conditions ic ON c.id = ic.condition_id
        JOIN issues i ON ic.issue_id = i.id
        WHERE i.decision_id = %s
    """, (decision_id,))
    row = cur.fetchone()
    assert row[0] == "tinnitus"
