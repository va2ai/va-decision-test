from typing import Optional
import psycopg

def find_similar_cases(
    conn: psycopg.Connection,
    query_text: str,
    limit: int = 5,
    outcome_filter: Optional[str] = None,
) -> list[dict]:
    """
    Find similar cases based on passage embeddings.

    Args:
        conn: Database connection
        query_text: Text to find similar passages for
        limit: Max results to return
        outcome_filter: Optional filter by outcome (Granted, Denied, etc.)

    Returns:
        List of dicts with passage, issue, condition, outcome, similarity score
    """
    # Note: This requires an embedding function to be called first
    # For now, we'll use a placeholder that works without embeddings

    query = """
        SELECT
            p.text as passage,
            i.issue_text,
            i.outcome,
            c.name as condition,
            d.decision_id
        FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        JOIN issues i ON ip.issue_id = i.id
        LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
        LEFT JOIN conditions c ON ic.condition_id = c.id
        JOIN decisions d ON p.decision_id = d.id
        WHERE 1=1
    """
    params = []

    if outcome_filter:
        query += " AND i.outcome = %s"
        params.append(outcome_filter)

    query += " LIMIT %s"
    params.append(limit)

    cur = conn.execute(query, params)
    results = []
    for row in cur.fetchall():
        results.append({
            "passage": row[0],
            "issue_text": row[1],
            "outcome": row[2],
            "condition": row[3],
            "decision_id": row[4],
        })

    return results

def find_similar_with_embedding(
    conn: psycopg.Connection,
    query_embedding: list[float],
    limit: int = 5,
    outcome_filter: Optional[str] = None,
) -> list[dict]:
    """
    Find similar cases using vector similarity.

    Args:
        conn: Database connection
        query_embedding: 768-dim embedding vector
        limit: Max results
        outcome_filter: Optional outcome filter

    Returns:
        List of similar passages with similarity scores
    """
    query = """
        SELECT
            p.text as passage,
            i.issue_text,
            i.outcome,
            c.name as condition,
            d.decision_id,
            1 - (p.embedding <=> %s::vector) as similarity
        FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        JOIN issues i ON ip.issue_id = i.id
        LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
        LEFT JOIN conditions c ON ic.condition_id = c.id
        JOIN decisions d ON p.decision_id = d.id
        WHERE p.embedding IS NOT NULL
    """
    params = [query_embedding]

    if outcome_filter:
        query += " AND i.outcome = %s"
        params.append(outcome_filter)

    query += " ORDER BY p.embedding <=> %s::vector LIMIT %s"
    params.extend([query_embedding, limit])

    cur = conn.execute(query, params)
    results = []
    for row in cur.fetchall():
        results.append({
            "passage": row[0],
            "issue_text": row[1],
            "outcome": row[2],
            "condition": row[3],
            "decision_id": row[4],
            "similarity": float(row[5]) if row[5] else 0.0,
        })

    return results
