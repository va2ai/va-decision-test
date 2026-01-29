import psycopg

def get_authority_stats(conn: psycopg.Connection, condition: str) -> list[dict]:
    """
    Get authority citation statistics by outcome for a condition.

    Returns citation counts grouped by outcome.
    """
    cur = conn.execute("""
        SELECT a.citation, i.outcome, COUNT(*) as count
        FROM authorities a
        JOIN decision_authorities da ON a.id = da.authority_id
        JOIN decisions d ON da.decision_id = d.id
        JOIN issues i ON i.decision_id = d.id
        JOIN issue_conditions ic ON i.id = ic.issue_id
        JOIN conditions c ON ic.condition_id = c.id
        WHERE c.name ILIKE %s
        GROUP BY a.citation, i.outcome
        ORDER BY count DESC
    """, (f"%{condition}%",))

    results = []
    for row in cur.fetchall():
        results.append({
            "citation": row[0],
            "outcome": row[1],
            "count": row[2],
        })

    return results
