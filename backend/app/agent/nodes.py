"""
The steps (nodes) of the agent graph. Each node takes the state and returns the fields it updates.
"""

from collections import Counter

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app import config
from app.agent.llm import get_chat_model, get_structured_model
from app.agent.prompts import (
    CLASSIFIER_PROMPT,
    DEBUG_PROMPT,
    DESTRUCTIVE_MESSAGE,
    EXPLAIN_CONCEPT_PROMPT,
    EXPLAIN_QUERY_PROMPT,
    EXPLAINER_PROMPT,
    GENERATOR_PROMPT,
    GENERATOR_RETRY_PROMPT,
    GIVE_UP_MESSAGE,
    OPTIMIZE_PROMPT,
    OUT_OF_SCOPE_MESSAGE,
    SCHEMA_INFO_PROMPT,
)
from app.agent.state import (
    AgentState,
    IntentClassification,
    SQLDebugResult,
    SQLGeneration,
    SQLOptimization,
)
from app.db.database import get_schema, get_schema_for_prompt, run_query
from app.validation.validator import ValidationResult, validate_sql

classifier_llm = get_structured_model(config.CLASSIFIER_MODEL, IntentClassification)
generator_llm = get_structured_model(config.GENERATOR_MODEL, SQLGeneration)
debugger_llm = get_structured_model(config.GENERATOR_MODEL, SQLDebugResult)
optimizer_llm = get_structured_model(config.GENERATOR_MODEL, SQLOptimization)
explainer_llm = get_chat_model(config.EXPLAINER_MODEL)

PREVIEW_ROWS = 5


def classify_intent(state: AgentState) -> dict:
    """Decide what kind of request the latest message is, and extract any SQL it contains."""
    system = SystemMessage(CLASSIFIER_PROMPT.format(table_names=", ".join(get_schema())))
    result = classifier_llm.invoke([system, *state["messages"]])
    return {
        "intent": result.intent,
        "user_sql": result.user_sql,
        "generated_sql": None,
        "generation_plan": None,
        "validation_errors": [],
        "validation_warnings": [],
        "retry_count": 0,
        "query_result": None,
        "explanation": None,
    }


def generate_sql(state: AgentState) -> dict:
    """Write a SQL query for the request. On a retry, the validator's errors are included."""
    system_text = GENERATOR_PROMPT.format(schema=get_schema_for_prompt())
    if state["validation_errors"]:
        system_text += "\n\n" + GENERATOR_RETRY_PROMPT.format(
            sql=state["generated_sql"],
            errors="\n".join(f"- {error}" for error in state["validation_errors"]),
        )

    result = generator_llm.invoke([SystemMessage(system_text), *state["messages"]])

    if not result.sql:
        question = result.clarification or "Could you rephrase your request with a bit more detail?"
        return {"generated_sql": None, "generation_plan": result.plan, "messages": [AIMessage(question)]}
    return {"generated_sql": result.sql, "generation_plan": result.plan}


def validate_query(state: AgentState) -> dict:
    """Check the generated SQL with the deterministic validator. Counts failed attempts."""
    result = validate_sql(state["generated_sql"], get_schema())
    return {
        "validation_errors": result.errors,
        "validation_warnings": result.warnings,
        "retry_count": state["retry_count"] + (0 if result.is_valid else 1),
    }


def execute_query(state: AgentState) -> dict:
    """Run the validated SQL. If SQLite still rejects it, treat that like a validation error."""
    try:
        return {"query_result": run_query(state["generated_sql"])}
    except Exception as error:
        return {
            "validation_errors": [f"The query failed when run on the database: {error}"],
            "retry_count": state["retry_count"] + 1,
        }


def latest_user_message(state: AgentState) -> str:
    return next(m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage))


def format_preview(result: dict) -> str:
    """The column names and first few rows as a small text table."""
    lines = [" | ".join(result["columns"])]
    lines += [" | ".join(str(value) for value in row) for row in result["rows"][:PREVIEW_ROWS]]
    return "\n".join(lines)


def explain(state: AgentState) -> dict:
    """Explain the query and its result in plain English, then reply with the SQL and explanation."""
    result = state["query_result"]
    prompt = EXPLAINER_PROMPT.format(
        question=latest_user_message(state),
        sql=state["generated_sql"],
        plan=state["generation_plan"] or "None",
        warnings="\n".join(state["validation_warnings"]) or "None",
        row_count=result["row_count"],
        truncated_note=" (only the first rows were returned; more exist)" if result["truncated"] else "",
        preview=format_preview(result),
    )
    explanation = explainer_llm.invoke([HumanMessage(prompt)]).text
    reply = f"```sql\n{state['generated_sql']}\n```\n\n{explanation}"
    return {"explanation": explanation, "messages": [AIMessage(reply)]}


def answer_schema_question(state: AgentState) -> dict:
    """Answer questions about which tables, columns and relationships exist."""
    system = SystemMessage(SCHEMA_INFO_PROMPT.format(schema=get_schema_for_prompt()))
    answer = explainer_llm.invoke([system, *state["messages"]]).text
    return {"messages": [AIMessage(answer)]}


def format_findings(result: ValidationResult) -> str:
    """The validator's errors and warnings as a bulleted list for a prompt."""
    problems = result.errors + result.warnings
    return "\n".join(f"- {problem}" for problem in problems) or "No problems found."


def explain_user_sql(state: AgentState) -> dict:
    """Explain the user's own SQL query, or a general SQL concept if no query was given."""
    schema = get_schema_for_prompt()
    if state["user_sql"]:
        findings = format_findings(validate_sql(state["user_sql"], get_schema()))
        prompt = EXPLAIN_QUERY_PROMPT.format(schema=schema, sql=state["user_sql"], findings=findings)
    else:
        prompt = EXPLAIN_CONCEPT_PROMPT.format(schema=schema)

    answer = explainer_llm.invoke([SystemMessage(prompt), *state["messages"]]).text
    return {"messages": [AIMessage(answer)]}


def describe_run(sql: str) -> str:
    """Try the query on the read-only database and describe what happened, for a prompt."""
    try:
        result = run_query(sql)
    except Exception as error:
        return f"It failed with this error: {error}"
    return f"It ran and returned {result['row_count']} rows. First rows:\n{format_preview(result)}"


def debug_user_sql(state: AgentState) -> dict:
    """Diagnose the user's broken query using real evidence, and offer a validated fix."""
    sql = state["user_sql"]
    if not sql:
        return {"messages": [AIMessage("Please paste the SQL query you would like me to debug.")]}

    schema = get_schema()
    validation = validate_sql(sql, schema)
    run_outcome = describe_run(sql) if validation.is_valid else "Not run, because the validator found errors."
    prompt = DEBUG_PROMPT.format(
        schema=get_schema_for_prompt(), sql=sql, findings=format_findings(validation), run_outcome=run_outcome
    )
    result = debugger_llm.invoke([SystemMessage(prompt), *state["messages"]])

    parts = [f"**Issue:** {result.issue}", result.explanation]
    fix_is_valid = validate_sql(result.corrected_sql, schema).is_valid
    if fix_is_valid:
        parts.append(f"**Corrected query:**\n```sql\n{result.corrected_sql}\n```")
    else:
        parts.append("I couldn't produce a corrected query that passes validation, so I'm not showing one.")
    return {
        "generated_sql": result.corrected_sql if fix_is_valid else None,
        "messages": [AIMessage("\n\n".join(parts))],
    }


def same_results(original_sql: str, new_sql: str) -> bool | None:
    """Run both queries and compare their rows, ignoring order. None if either query fails."""
    try:
        original, new = run_query(original_sql), run_query(new_sql)
    except Exception:
        return None
    return Counter(map(tuple, original["rows"])) == Counter(map(tuple, new["rows"]))


def optimize_user_sql(state: AgentState) -> dict:
    """Improve a working query, then check the new version is valid and returns the same rows."""
    sql = state["user_sql"]
    if not sql:
        return {"messages": [AIMessage("Please paste the SQL query you would like me to optimize.")]}

    schema = get_schema()
    validation = validate_sql(sql, schema)
    if not validation.is_valid:
        reply = (
            "This query has problems that need fixing before it can be optimized:\n\n"
            f"{format_findings(validation)}\n\nAsk me to debug it and I'll suggest a fix."
        )
        return {"messages": [AIMessage(reply)]}

    prompt = OPTIMIZE_PROMPT.format(schema=get_schema_for_prompt(), sql=sql)
    result = optimizer_llm.invoke([SystemMessage(prompt), *state["messages"]])

    parts = ["**Changes:**\n" + "\n".join(f"- {change}" for change in result.changes)]
    if result.index_suggestions:
        parts.append("**Suggested indexes:**\n```sql\n" + "\n".join(result.index_suggestions) + "\n```")

    fix_is_valid = validate_sql(result.optimized_sql, schema).is_valid
    if not fix_is_valid:
        parts.append("The rewritten query did not pass validation, so I'm keeping your original query.")
        return {"messages": [AIMessage("\n\n".join(parts))]}

    parts.append(f"**Optimized query:**\n```sql\n{result.optimized_sql}\n```")
    if same_results(sql, result.optimized_sql):
        parts.append("Checked: it returns the same rows as your original query.")
    else:
        parts.append("Warning: it does not return the same rows as your original query. Review it before using it.")
    return {"generated_sql": result.optimized_sql, "messages": [AIMessage("\n\n".join(parts))]}


def give_up(state: AgentState) -> dict:
    """Stop after too many invalid attempts instead of returning SQL we know is broken."""
    return {"messages": [AIMessage(GIVE_UP_MESSAGE)]}


def refuse(state: AgentState) -> dict:
    """Politely decline destructive or out-of-scope requests. Fixed text, no LLM call."""
    message = DESTRUCTIVE_MESSAGE if state["intent"] == "destructive" else OUT_OF_SCOPE_MESSAGE
    return {"messages": [AIMessage(message)]}
