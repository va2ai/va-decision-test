import pytest
from src.db.connection import get_connection, init_schema

def test_schema_creates_tables():
    conn = get_connection()
    init_schema(conn)

    cur = conn.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]

    assert "decisions" in tables
    assert "issues" in tables
    assert "conditions" in tables
    assert "authorities" in tables
    assert "evidence_types" in tables
    assert "passages" in tables
    assert "issue_conditions" in tables
    conn.close()
