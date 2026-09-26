"""
Database access for the agent.

All connections are read-only: even if a destructive query slipped past the
validator, SQLite itself would refuse to change anything.
"""

import sqlite3
import time
from contextlib import closing

from app.config import DB_PATH

MAX_LISTED_VALUES = 20
EXAMPLE_VALUE_COUNT = 3
MAX_RESULT_ROWS = 500
QUERY_TIMEOUT_SECONDS = 5


def get_connection() -> sqlite3.Connection:
    """Open the database in read-only mode."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run: python -m app.db.seed")
    return sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)


def get_schema() -> dict[str, dict]:
    """Every table with its columns (name -> type) and foreign keys, read from the database itself."""
    schema = {}
    with closing(get_connection()) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            columns = {
                name: column_type
                for name, column_type in conn.execute(
                    "SELECT name, type FROM pragma_table_info(?)", (table,)
                )
            }
            foreign_keys = [
                {"column": column, "references_table": ref_table, "references_column": ref_column}
                for column, ref_table, ref_column in conn.execute(
                    'SELECT "from", "table", "to" FROM pragma_foreign_key_list(?)', (table,)
                )
            ]
            schema[table] = {"columns": columns, "foreign_keys": foreign_keys}
    return schema


def format_value(value: object) -> str:
    """Show text in single quotes (as it must appear in SQL) and numbers as-is."""
    return f"'{value}'" if isinstance(value, str) else str(value)


def describe_column_values(conn: sqlite3.Connection, table: str, column: str) -> str:
    """All values for columns with few distinct values, otherwise a few examples."""
    distinct_count = conn.execute(f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"').fetchone()[0]
    if distinct_count <= MAX_LISTED_VALUES:
        label = "all values"
        query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL ORDER BY 1'
    else:
        label = "examples"
        query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT {EXAMPLE_VALUE_COUNT}'
    values = ", ".join(format_value(row[0]) for row in conn.execute(query))
    return f"{label}: {values}"


def get_schema_for_prompt() -> str:
    """CREATE TABLE statements (with their comments) plus sample column values, for the LLM."""
    schema = get_schema()
    sections = []
    with closing(get_connection()) as conn:
        for table, details in schema.items():
            create_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
            ).fetchone()[0]
            lines = [f"{create_sql};", "Sample values:"]
            for column in details["columns"]:
                if column.endswith("_id"):
                    continue
                lines.append(f"  {column} ({describe_column_values(conn, table, column)})")
            sections.append("\n".join(lines))
    return "\n\n".join(sections)


def run_query(sql: str) -> dict:
    """Run a query and return at most MAX_RESULT_ROWS rows. Stops it if it runs too long."""
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    with closing(get_connection()) as conn:
        conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)
        try:
            cursor = conn.execute(sql)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        except sqlite3.OperationalError as error:
            if "interrupted" in str(error):
                raise TimeoutError(
                    f"Query took longer than {QUERY_TIMEOUT_SECONDS} seconds and was stopped."
                ) from error
            raise

    truncated = len(rows) > MAX_RESULT_ROWS
    rows = rows[:MAX_RESULT_ROWS]
    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }
