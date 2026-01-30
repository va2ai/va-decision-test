#!/usr/bin/env python3
"""
Migration: Add dual-score columns to existing issues table.

Run this if you have an existing database from before the LEGALBENCH enhancements.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.connection import get_connection


def migrate():
    conn = get_connection()

    print("Adding dual-score columns to issues table...")

    try:
        conn.execute("""
            ALTER TABLE issues
            ADD COLUMN IF NOT EXISTS correctness_score FLOAT DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS analysis_depth_score FLOAT DEFAULT NULL
        """)
        conn.commit()
        print("Migration complete - dual-score columns added")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

    return True


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
