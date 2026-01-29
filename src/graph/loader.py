import logging
from typing import Optional
import psycopg
from src.extraction.models import ExtractionResult

logger = logging.getLogger(__name__)

def get_or_create_condition(conn: psycopg.Connection, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO conditions (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        (name,)
    )
    return cur.fetchone()[0]

def get_or_create_authority(conn: psycopg.Connection, citation: str) -> int:
    cur = conn.execute(
        "INSERT INTO authorities (citation) VALUES (%s) ON CONFLICT (citation) DO UPDATE SET citation = EXCLUDED.citation RETURNING id",
        (citation,)
    )
    return cur.fetchone()[0]

def get_or_create_evidence_type(conn: psycopg.Connection, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO evidence_types (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        (name,)
    )
    return cur.fetchone()[0]

def get_or_create_provider_type(conn: psycopg.Connection, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO provider_types (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        (name,)
    )
    return cur.fetchone()[0]

def load_decision(
    conn: psycopg.Connection,
    decision_id: str,
    raw_text: str,
    extraction: ExtractionResult,
    decision_date: Optional[str] = None,
    embedding: Optional[list[float]] = None,
) -> int:
    """
    Load a decision and its extracted entities into the database.

    Returns the database ID of the created decision.
    """
    # Insert decision
    cur = conn.execute(
        """
        INSERT INTO decisions (decision_id, decision_date, system_type, raw_text, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (decision_id) DO UPDATE SET
            decision_date = EXCLUDED.decision_date,
            system_type = EXCLUDED.system_type,
            raw_text = EXCLUDED.raw_text,
            embedding = EXCLUDED.embedding
        RETURNING id
        """,
        (decision_id, decision_date, extraction.system_type, raw_text, embedding)
    )
    db_decision_id = cur.fetchone()[0]

    # Insert authorities and link to decision
    for citation in extraction.authorities:
        auth_id = get_or_create_authority(conn, citation)
        conn.execute(
            "INSERT INTO decision_authorities (decision_id, authority_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (db_decision_id, auth_id)
        )

    # Insert issues
    for issue in extraction.issues:
        cur = conn.execute(
            """
            INSERT INTO issues (decision_id, issue_text, outcome, connection_type)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (db_decision_id, issue.issue_text, issue.outcome, issue.connection_type)
        )
        issue_id = cur.fetchone()[0]

        # Link condition
        if issue.condition:
            cond_id = get_or_create_condition(conn, issue.condition)
            conn.execute(
                "INSERT INTO issue_conditions (issue_id, condition_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (issue_id, cond_id)
            )

        # Link evidence types
        for ev in issue.evidence_types:
            ev_id = get_or_create_evidence_type(conn, ev)
            conn.execute(
                "INSERT INTO issue_evidence (issue_id, evidence_type_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (issue_id, ev_id)
            )

        # Link provider types
        for prov in issue.provider_types:
            prov_id = get_or_create_provider_type(conn, prov)
            conn.execute(
                "INSERT INTO issue_providers (issue_id, provider_type_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (issue_id, prov_id)
            )

    # Insert passages
    for passage in extraction.passages:
        cur = conn.execute(
            """
            INSERT INTO passages (decision_id, text, tag, confidence)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (db_decision_id, passage.text, passage.tag, passage.confidence)
        )
        passage_id = cur.fetchone()[0]

        # Link passage to all issues (simplified - could be smarter)
        for issue in extraction.issues:
            # Get issue ID by text match
            cur2 = conn.execute(
                "SELECT id FROM issues WHERE decision_id = %s AND issue_text = %s",
                (db_decision_id, issue.issue_text)
            )
            if row := cur2.fetchone():
                conn.execute(
                    "INSERT INTO issue_passages (issue_id, passage_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (row[0], passage_id)
                )

    conn.commit()
    logger.info(f"Loaded decision {decision_id} with {len(extraction.issues)} issues")
    return db_decision_id
