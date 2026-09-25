"""
Database access for the agent.

All connections are read-only: even if a destructive query slipped past the
validator, SQLite itself would refuse to change anything.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "company.db"


def get_connection() -> sqlite3.Connection:
    """Open the database in read-only mode."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run: python app/db/seed.py")
    return sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
