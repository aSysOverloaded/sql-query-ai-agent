"""
Query cost estimation from SQLite's EXPLAIN QUERY PLAN. Deterministic: no LLM, and the query is not run.

SQLite does not report a numeric cost, so the estimate counts the rows of tables that are read in full
(SCAN steps) and turns the plan into plain-English notes. Scans under the same parent step are nested
loops (each runs once per row of the previous one), so their row counts multiply.
"""

import math
import re
from collections import defaultdict
from contextlib import closing

import sqlglot
from sqlglot import exp

from app.db.database import get_connection, get_schema

LOW_COST_MAX_ROWS = 1_000
MEDIUM_COST_MAX_ROWS = 10_000

SCAN_PATTERN = re.compile(r"^SCAN (\w+)(?: USING (?:COVERING )?INDEX (\w+))?")
SEARCH_PATTERN = re.compile(r"^SEARCH (\w+) USING (.+)")
SORT_PATTERN = re.compile(r"USE TEMP B-TREE FOR (ORDER BY|GROUP BY|DISTINCT)")


def alias_to_table(sql: str, table_names: set[str]) -> dict[str, str]:
    """Map every alias used in the query (e.g. 'o') to its real table (e.g. 'orders')."""
    tree = sqlglot.parse_one(sql, dialect="sqlite")
    return {
        table.alias_or_name.lower(): table.name.lower()
        for table in tree.find_all(exp.Table)
        if table.name.lower() in table_names
    }


def describe_step(detail: str, tables: dict[str, str], row_counts: dict[str, int]) -> tuple[str | None, int]:
    """One plan step as a plain-English note, plus how many rows it reads in full."""
    if match := SCAN_PATTERN.match(detail):
        table = tables.get(match.group(1).lower())
        if table is None:
            return None, 0
        via_index = " through an index" if match.group(2) else ""
        return f"Reads every row of {table}{via_index} ({row_counts[table]:,} rows).", row_counts[table]

    if match := SEARCH_PATTERN.match(detail):
        table = tables.get(match.group(1).lower(), match.group(1))
        method = match.group(2)
        if "AUTOMATIC" in method:
            return f"Builds a temporary index on {table} for this query; a permanent index could help.", 0
        if "PRIMARY KEY" in method:
            return f"Looks up {table} rows directly by primary key.", 0
        return f"Uses an index to find rows in {table}.", 0

    if match := SORT_PATTERN.search(detail):
        return f"Uses a temporary sort for {match.group(1)}.", 0

    return None, 0


def estimate_query_cost(sql: str) -> dict:
    """Return {'level', 'rows_scanned', 'notes', 'plan'} for a validated read-only query."""
    table_names = set(get_schema())
    tables = alias_to_table(sql, table_names)
    with closing(get_connection()) as conn:
        plan = [(row[1], row[3]) for row in conn.execute(f"EXPLAIN QUERY PLAN {sql}")]
        row_counts = {name: conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in set(tables.values())}

    notes = []
    scans_by_parent = defaultdict(list)
    for parent, detail in plan:
        note, rows = describe_step(detail, tables, row_counts)
        if rows:
            scans_by_parent[parent].append(rows)
        if note and note not in notes:
            notes.append(note)
    rows_scanned = sum(math.prod(scans) for scans in scans_by_parent.values())

    if rows_scanned <= LOW_COST_MAX_ROWS:
        level = "low"
    elif rows_scanned <= MEDIUM_COST_MAX_ROWS:
        level = "medium"
    else:
        level = "high"
    return {"level": level, "rows_scanned": rows_scanned, "notes": notes, "plan": [detail for _, detail in plan]}
