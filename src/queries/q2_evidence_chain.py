import psycopg

def get_evidence_chain(conn: psycopg.Connection, issue_id: int) -> dict:
    """
    Get the full evidence chain for an issue.

    Returns condition, evidence types, providers, authorities, and quotes.
    """
    result = {
        "issue_id": issue_id,
        "condition": None,
        "evidence_types": [],
        "provider_types": [],
        "authorities": [],
        "passages": [],
    }

    # Get condition
    cur = conn.execute("""
        SELECT c.name FROM conditions c
        JOIN issue_conditions ic ON c.id = ic.condition_id
        WHERE ic.issue_id = %s
    """, (issue_id,))
    if row := cur.fetchone():
        result["condition"] = row[0]

    # Get evidence types
    cur = conn.execute("""
        SELECT et.name FROM evidence_types et
        JOIN issue_evidence ie ON et.id = ie.evidence_type_id
        WHERE ie.issue_id = %s
    """, (issue_id,))
    result["evidence_types"] = [row[0] for row in cur.fetchall()]

    # Get provider types
    cur = conn.execute("""
        SELECT pt.name FROM provider_types pt
        JOIN issue_providers ip ON pt.id = ip.provider_type_id
        WHERE ip.issue_id = %s
    """, (issue_id,))
    result["provider_types"] = [row[0] for row in cur.fetchall()]

    # Get authorities (via decision)
    cur = conn.execute("""
        SELECT a.citation FROM authorities a
        JOIN decision_authorities da ON a.id = da.authority_id
        JOIN issues i ON da.decision_id = i.decision_id
        WHERE i.id = %s
    """, (issue_id,))
    result["authorities"] = [row[0] for row in cur.fetchall()]

    # Get passages
    cur = conn.execute("""
        SELECT p.text, p.tag FROM passages p
        JOIN issue_passages ip ON p.id = ip.passage_id
        WHERE ip.issue_id = %s
    """, (issue_id,))
    result["passages"] = [{"text": row[0], "tag": row[1]} for row in cur.fetchall()]

    return result
