"""
Deterministic SQL validation. No LLM involved.

Errors mean the query is rejected (and sent back to the LLM to fix).
Warnings are shown to the user, but the query still runs.
"""

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, ParseError
from sqlglot.optimizer.qualify import qualify

WRITE_OPERATIONS = {
    exp.Insert: "INSERT",
    exp.Update: "UPDATE",
    exp.Delete: "DELETE",
    exp.Drop: "DROP",
    exp.Alter: "ALTER",
    exp.TruncateTable: "TRUNCATE",
    exp.Create: "CREATE",
    exp.Merge: "MERGE",
    exp.Attach: "ATTACH",
    exp.Detach: "DETACH",
    exp.Pragma: "PRAGMA",
    exp.Transaction: "BEGIN",
}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def parse_single_statement(sql: str, result: ValidationResult) -> exp.Expression | None:
    """Return the parsed statement, or record an error and return None."""
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="sqlite") if s is not None]
    except ParseError as error:
        details = error.errors[0]
        result.errors.append(
            f"SQL syntax error near line {details.get('line')}, column {details.get('col')}: "
            f"{details.get('description')}"
        )
        return None

    if not statements:
        result.errors.append("The query is empty.")
        return None
    if len(statements) > 1:
        result.errors.append(
            f"Only one SQL statement is allowed, but {len(statements)} were found."
        )
        return None
    return statements[0]


def check_read_only(tree: exp.Expression, sql: str, result: ValidationResult) -> bool:
    """The statement must be a query (SELECT, UNION, ...) with no write operation anywhere inside."""
    for node in tree.walk():
        operation = WRITE_OPERATIONS.get(type(node))
        if operation:
            result.errors.append(f"Only read-only SELECT queries are allowed. Found: {operation}.")
            return False

    if not isinstance(tree, exp.Query):
        first_word = sql.split()[0].upper()
        result.errors.append(f"Only read-only SELECT queries are allowed. Found: {first_word}.")
        return False

    return True


def check_tables_exist(tree: exp.Expression, schema: dict[str, dict], result: ValidationResult) -> bool:
    """Every table referenced must exist in the schema. Names defined by WITH (CTEs) are allowed."""
    known_tables = {name.lower() for name in schema}
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}

    unknown_tables = sorted(
        {
            table.name
            for table in tree.find_all(exp.Table)
            if table.name.lower() not in known_tables | cte_names
        }
    )
    for name in unknown_tables:
        result.errors.append(
            f"Unknown table '{name}'. Available tables: {', '.join(sorted(schema))}."
        )
    return not unknown_tables


def check_columns_exist(tree: exp.Expression, schema: dict[str, dict], result: ValidationResult) -> bool:
    """Every column must exist in the table it refers to. Handles aliases, CTEs and subqueries."""
    columns_by_table = {table: details["columns"] for table, details in schema.items()}
    try:
        qualify(tree.copy(), schema=columns_by_table, dialect="sqlite", validate_qualify_columns=True)
    except OptimizeError as error:
        used_tables = sorted({table.name.lower() for table in tree.find_all(exp.Table)} & set(schema))
        available = "; ".join(
            f"{table}({', '.join(schema[table]['columns'])})" for table in used_tables
        )
        result.errors.append(f"{str(error).rstrip('.')}. Available columns: {available}.")
        return False
    return True


def check_join_relationships(tree: exp.Expression, schema: dict[str, dict], result: ValidationResult) -> None:
    """Warn when a simple JOIN condition (a.col = b.col) is not a foreign key. Never blocks the query."""
    alias_to_table = {
        table.alias_or_name.lower(): table.name.lower()
        for table in tree.find_all(exp.Table)
        if table.name.lower() in schema
    }
    relationships = {
        frozenset(
            {
                (table, foreign_key["column"].lower()),
                (foreign_key["references_table"].lower(), foreign_key["references_column"].lower()),
            }
        )
        for table, details in schema.items()
        for foreign_key in details["foreign_keys"]
    }

    for join in tree.find_all(exp.Join):
        condition = join.args.get("on")
        if not isinstance(condition, exp.EQ):
            continue
        left, right = condition.this, condition.expression
        if not (isinstance(left, exp.Column) and isinstance(right, exp.Column)):
            continue
        left_table = alias_to_table.get(left.table.lower())
        right_table = alias_to_table.get(right.table.lower())
        if not left_table or not right_table:
            continue

        pair = frozenset({(left_table, left.name.lower()), (right_table, right.name.lower())})
        if pair not in relationships:
            result.warnings.append(
                f"Join condition {left_table}.{left.name} = {right_table}.{right.name} does not follow "
                f"a defined relationship (foreign key). Check that this join is intended."
            )


def validate_sql(sql: str, schema: dict[str, dict]) -> ValidationResult:
    """Run all checks against the given schema (the output of get_schema())."""
    result = ValidationResult()

    tree = parse_single_statement(sql, result)
    if tree is None:
        return result

    if not check_read_only(tree, sql, result):
        return result

    if not check_tables_exist(tree, schema, result):
        return result

    if not check_columns_exist(tree, schema, result):
        return result

    check_join_relationships(tree, schema, result)
    return result
