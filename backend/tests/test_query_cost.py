"""
Tests for query cost estimation (EXPLAIN QUERY PLAN). Uses the seeded database; no LLM.
"""

import pytest

from app.db.query_cost import estimate_query_cost

pytestmark = pytest.mark.usefixtures("seeded_database")


def test_primary_key_lookup_reads_no_full_table():
    cost = estimate_query_cost("SELECT * FROM customers WHERE customer_id = 5")
    assert cost["level"] == "low"
    assert cost["rows_scanned"] == 0
    assert cost["notes"] == ["Looks up customers rows directly by primary key."]


def test_full_scan_counts_the_table_rows():
    cost = estimate_query_cost("SELECT * FROM customers WHERE state = 'CA'")
    assert cost["rows_scanned"] == 200
    assert "Reads every row of customers (200 rows)." in cost["notes"]


def test_aliases_are_mapped_to_real_tables():
    cost = estimate_query_cost(
        "SELECT c.first_name, COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id "
        "GROUP BY c.customer_id"
    )
    assert cost["rows_scanned"] == 1000
    assert "Reads every row of orders (1,000 rows)." in cost["notes"]
    assert "Looks up customers rows directly by primary key." in cost["notes"]


def test_nested_scans_multiply_and_are_high_cost():
    cost = estimate_query_cost("SELECT COUNT(*) FROM order_items a, customers c")
    assert cost["rows_scanned"] == 2973 * 200
    assert cost["level"] == "high"


def test_large_table_scan_is_medium_cost():
    cost = estimate_query_cost("SELECT product_id, SUM(quantity) FROM order_items GROUP BY product_id")
    assert cost["level"] == "medium"
    assert cost["rows_scanned"] == 2973


def test_temporary_index_is_reported_as_an_index_hint():
    cost = estimate_query_cost(
        "SELECT p.name FROM products p LEFT JOIN order_items oi ON oi.product_id = p.product_id "
        "WHERE oi.order_item_id IS NULL"
    )
    assert any("a permanent index could help" in note for note in cost["notes"])


def test_cte_names_are_not_counted_as_tables():
    cost = estimate_query_cost(
        "WITH t AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) SELECT * FROM t WHERE n > 5"
    )
    assert cost["rows_scanned"] == 1000
