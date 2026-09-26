"""
Unit tests for the deterministic SQL validator. Uses a small in-test schema, so no database or LLM is needed.
"""

import pytest

from app.validation.validator import validate_sql

SCHEMA = {
    "customers": {
        "columns": {"customer_id": "INTEGER", "name": "TEXT", "state": "TEXT"},
        "foreign_keys": [],
    },
    "orders": {
        "columns": {"order_id": "INTEGER", "customer_id": "INTEGER", "order_date": "TEXT"},
        "foreign_keys": [
            {"column": "customer_id", "references_table": "customers", "references_column": "customer_id"}
        ],
    },
    "employees": {
        "columns": {"employee_id": "INTEGER", "first_name": "TEXT", "manager_id": "INTEGER"},
        "foreign_keys": [
            {"column": "manager_id", "references_table": "employees", "references_column": "employee_id"}
        ],
    },
}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customers",
        "SELECT name FROM customers WHERE state = 'CA';",
        "SELECT * FROM CUSTOMERS",
        "SELECT c.name, o.order_date FROM customers c JOIN orders o ON o.customer_id = c.customer_id",
        "SELECT e.first_name, m.first_name FROM employees e LEFT JOIN employees m ON e.manager_id = m.employee_id",
        "WITH ca AS (SELECT customer_id FROM customers WHERE state = 'CA') SELECT * FROM ca",
        "SELECT * FROM customers WHERE customer_id IN (SELECT customer_id FROM orders)",
        "SELECT name FROM customers UNION SELECT first_name FROM employees",
        "SELECT state, COUNT(*) AS total FROM customers GROUP BY state ORDER BY total DESC",
        "SELECT p.name FROM (SELECT name FROM customers) AS p",
    ],
)
def test_valid_queries_pass(sql):
    result = validate_sql(sql, SCHEMA)
    assert result.is_valid, result.errors


@pytest.mark.parametrize(
    "sql",
    ["SELEC * FROM customers", "SELECT * FROM", "SELECT name FROM customers WHERE", "SELECT (1 + FROM customers"],
)
def test_syntax_errors_are_rejected(sql):
    result = validate_sql(sql, SCHEMA)
    assert not result.is_valid
    assert result.errors[0].startswith("SQL syntax error")


@pytest.mark.parametrize("sql", ["", "   ", ";"])
def test_empty_query_is_rejected(sql):
    assert validate_sql(sql, SCHEMA).errors == ["The query is empty."]


def test_multiple_statements_are_rejected():
    result = validate_sql("SELECT * FROM customers; DROP TABLE orders", SCHEMA)
    assert result.errors == ["Only one SQL statement is allowed, but 2 were found."]


@pytest.mark.parametrize(
    ("sql", "operation"),
    [
        ("DELETE FROM customers", "DELETE"),
        ("UPDATE customers SET name = 'x'", "UPDATE"),
        ("INSERT INTO customers (name) VALUES ('x')", "INSERT"),
        ("DROP TABLE orders", "DROP"),
        ("ALTER TABLE orders ADD COLUMN x INT", "ALTER"),
        ("TRUNCATE TABLE orders", "TRUNCATE"),
        ("CREATE TABLE t (a INT)", "CREATE"),
        ("REPLACE INTO customers (name) VALUES ('x')", "REPLACE"),
        ("ATTACH DATABASE 'other.db' AS other", "ATTACH"),
        ("PRAGMA foreign_keys = OFF", "PRAGMA"),
        ("VACUUM", "VACUUM"),
        ("REINDEX", "REINDEX"),
        ("BEGIN", "BEGIN"),
        ("WITH x AS (SELECT 1) DELETE FROM customers", "DELETE"),
    ],
)
def test_write_operations_are_rejected(sql, operation):
    result = validate_sql(sql, SCHEMA)
    assert result.errors == [f"Only read-only SELECT queries are allowed. Found: {operation}."]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customer",
        "SELECT * FROM customers c JOIN sales s ON s.customer_id = c.customer_id",
        "WITH x AS (SELECT * FROM order) SELECT * FROM x",
        "SELECT * FROM customers WHERE customer_id IN (SELECT customer_id FROM purchases)",
    ],
)
def test_unknown_tables_are_rejected(sql):
    result = validate_sql(sql, SCHEMA)
    assert not result.is_valid
    assert result.errors[0].startswith("Unknown table")
    assert "Available tables: customers, employees, orders." in result.errors[0]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT nme FROM customers",
        "SELECT c.first_name FROM customers c",
        "SELECT x.name FROM customers c",
        "SELECT customer_id FROM customers c JOIN orders o ON o.customer_id = c.customer_id",
        "SELECT * FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.total > 5)",
        "WITH ca AS (SELECT customer_id FROM customers) SELECT name FROM ca",
    ],
)
def test_unknown_or_ambiguous_columns_are_rejected(sql):
    result = validate_sql(sql, SCHEMA)
    assert not result.is_valid
    assert "Available columns:" in result.errors[0]


def test_column_error_lists_the_columns_of_the_tables_used():
    error = validate_sql("SELECT nme FROM customers", SCHEMA).errors[0]
    assert "customers(customer_id, name, state)" in error
    assert "orders(" not in error


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.customer_id",
        "SELECT * FROM orders o JOIN customers c ON c.customer_id = o.customer_id",
        "SELECT * FROM employees e JOIN employees m ON e.manager_id = m.employee_id",
        "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.customer_id",
    ],
)
def test_foreign_key_joins_have_no_warning(sql):
    result = validate_sql(sql, SCHEMA)
    assert result.is_valid
    assert result.warnings == []


def test_non_foreign_key_join_warns_but_stays_valid():
    result = validate_sql("SELECT * FROM customers c JOIN employees e ON c.name = e.first_name", SCHEMA)
    assert result.is_valid
    assert result.warnings == [
        "Join condition customers.name = employees.first_name does not follow a defined relationship "
        "(foreign key). Check that this join is intended."
    ]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.customer_id AND c.state = 'CA'",
        "SELECT * FROM orders o JOIN customers c USING (customer_id)",
        "WITH x AS (SELECT customer_id FROM orders) SELECT * FROM x JOIN customers c ON x.customer_id = c.customer_id",
    ],
)
def test_complex_joins_are_not_checked(sql):
    result = validate_sql(sql, SCHEMA)
    assert result.is_valid
    assert result.warnings == []
