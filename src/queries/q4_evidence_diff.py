import psycopg

def compare_evidence_by_outcome(conn: psycopg.Connection, condition: str) -> list[dict]:
    """
    Compare evidence types between granted and denied outcomes for a condition.

    Returns counts of each evidence type by outcome.
    """
    cur = conn.execute("""
        SELECT et.name as evidence_type, i.outcome, COUNT(*) as count
        FROM evidence_types et
        JOIN issue_evidence ie ON et.id = ie.evidence_type_id
        JOIN issues i ON ie.issue_id = i.id
        JOIN issue_conditions ic ON i.id = ic.issue_id
        JOIN conditions c ON ic.condition_id = c.id
        WHERE c.name ILIKE %s
        GROUP BY et.name, i.outcome
        ORDER BY et.name, i.outcome
    """, (f"%{condition}%",))

    results = []
    for row in cur.fetchall():
        results.append({
            "evidence_type": row[0],
            "outcome": row[1],
            "count": row[2],
        })

    return results
