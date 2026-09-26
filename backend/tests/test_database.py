"""
Tests for database access: read-only safety, query limits, schema reading and the seed data.
"""

import sqlite3
from contextlib import closing

import pytest

from app.db import database
from app.db.database import get_connection, get_schema, get_schema_for_prompt, run_query

pytestmark = pytest.mark.usefixtures("seeded_database")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "UPDATE products SET price = 0",
        "INSERT INTO categories (name) VALUES ('Hacked')",
        "DROP TABLE orders",
    ],
)
def test_connection_is_read_only(sql):
    with closing(get_connection()) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute(sql)
        assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 200


def test_missing_database_gives_a_helpful_error(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "missing.db")
    with pytest.raises(FileNotFoundError, match="python -m app.db.seed"):
        get_connection()


def test_run_query_returns_columns_and_rows():
    result = run_query("SELECT name FROM categories ORDER BY name")
    assert result == {
        "columns": ["name"],
        "rows": [["Books"], ["Clothing"], ["Electronics"], ["Home & Kitchen"], ["Sports"], ["Toys"]],
        "row_count": 6,
        "truncated": False,
    }


def test_run_query_caps_large_results():
    result = run_query("SELECT * FROM order_items")
    assert result["row_count"] == database.MAX_RESULT_ROWS
    assert result["truncated"] is True


def test_run_query_stops_slow_queries(monkeypatch):
    monkeypatch.setattr(database, "QUERY_TIMEOUT_SECONDS", 0.2)
    with pytest.raises(TimeoutError, match="was stopped"):
        run_query("SELECT COUNT(*) FROM order_items a, order_items b, customers c")


def test_run_query_passes_through_sqlite_errors():
    with pytest.raises(sqlite3.OperationalError, match="no such column"):
        run_query("SELECT nonexistent_column FROM customers")


def test_schema_has_all_tables_and_foreign_keys():
    schema = get_schema()
    assert sorted(schema) == [
        "categories", "customers", "departments", "employees", "order_items", "orders", "products"
    ]
    assert schema["employees"]["columns"]["hire_date"] == "TEXT"
    assert {
        "column": "manager_id",
        "references_table": "employees",
        "references_column": "employee_id",
    } in schema["employees"]["foreign_keys"]
    assert len(schema["order_items"]["foreign_keys"]) == 2


def test_schema_for_prompt_includes_comments_and_sample_values():
    text = get_schema_for_prompt()
    assert "CREATE TABLE customers" in text
    assert "2-letter code like 'CA'" in text
    assert "status (all values: 'cancelled', 'delivered', 'pending', 'shipped')" in text
    assert "country (all values: 'Canada', 'UK', 'USA')" in text
    assert "customer_id (" not in text


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT COUNT(*) FROM employees WHERE hire_date >= '2024-01-01'", [[9]]),
        ("SELECT COUNT(*) FROM customers WHERE state = 'CA'", [[26]]),
        (
            "SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status",
            [["cancelled", 85], ["delivered", 850], ["pending", 35], ["shipped", 30]],
        ),
        (
            "SELECT p.name FROM products p LEFT JOIN order_items oi ON oi.product_id = p.product_id "
            "WHERE oi.order_item_id IS NULL ORDER BY p.name",
            [["Kite"], ["Science Experiment Kit"]],
        ),
    ],
)
def test_seed_data_matches_documented_facts(sql, expected):
    assert run_query(sql)["rows"] == expected
