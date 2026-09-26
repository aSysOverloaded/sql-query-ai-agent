"""
Agent graph tests. Every LLM is replaced by a scripted fake, so these check the workflow wiring
(routing, retries, validation, memory) without any API calls.
"""

import uuid

import pytest
from langchain_core.messages import HumanMessage

from app.agent.graph import agent
from app.agent.prompts import DESTRUCTIVE_MESSAGE, GIVE_UP_MESSAGE, OUT_OF_SCOPE_MESSAGE
from app.agent.state import IntentClassification, SQLDebugResult, SQLGeneration, SQLOptimization
from tests.conftest import FakeLLM

VALID_SQL = "SELECT name FROM categories ORDER BY name"


def classified(intent, user_sql=None):
    return FakeLLM(IntentClassification(reason="test", intent=intent, user_sql=user_sql))


def generated(*sqls):
    return FakeLLM(*[SQLGeneration(plan="test plan", sql=sql) for sql in sqls])


def ask(message, thread_id=None):
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    return agent.invoke({"messages": [HumanMessage(message)]}, config=config)


@pytest.mark.parametrize(
    ("intent", "reply"), [("destructive", DESTRUCTIVE_MESSAGE), ("out_of_scope", OUT_OF_SCOPE_MESSAGE)]
)
def test_refusals_use_fixed_text_without_generating_sql(use_fakes, intent, reply):
    fakes = use_fakes(classifier=classified(intent))
    state = ask("anything")
    assert state["messages"][-1].content == reply
    assert fakes["generator"].calls == []


def test_sql_question_is_generated_validated_executed_and_explained(use_fakes):
    fakes = use_fakes(
        classifier=classified("generate_sql"),
        generator=generated(VALID_SQL),
        explainer=FakeLLM("There are six categories."),
    )

    state = ask("List the categories")

    assert state["query_result"]["row_count"] == 6
    assert state["explanation"] == "There are six categories."
    assert state["messages"][-1].content == f"```sql\n{VALID_SQL}\n```\n\nThere are six categories."
    assert len(fakes["generator"].calls) == 1


def test_broken_sql_is_retried_with_the_validator_errors(use_fakes):
    fakes = use_fakes(
        classifier=classified("generate_sql"),
        generator=generated("SELECT nme FROM products", VALID_SQL),
        explainer=FakeLLM("Fixed."),
    )

    state = ask("List the categories")

    retry_prompt = fakes["generator"].calls[1][0].content
    assert "Previous query:\nSELECT nme FROM products" in retry_prompt
    assert "Column 'nme' could not be resolved" in retry_prompt
    assert state["query_result"]["row_count"] == 6
    assert state["retry_count"] == 1


def test_sql_that_stays_broken_gives_up_after_three_attempts(use_fakes):
    fakes = use_fakes(classifier=classified("generate_sql"), generator=generated("SELECT nme FROM products"))

    state = ask("Product names")

    assert len(fakes["generator"].calls) == 3
    assert state["messages"][-1].content == GIVE_UP_MESSAGE
    assert state["validation_errors"]
    assert state["query_result"] is None


def test_database_errors_are_retried_like_validation_errors(use_fakes):
    fakes = use_fakes(
        classifier=classified("generate_sql"),
        generator=generated("SELECT SUM(COUNT(*)) FROM orders", "SELECT COUNT(*) FROM orders"),
        explainer=FakeLLM("1000 orders."),
    )

    state = ask("How many orders?")

    retry_prompt = fakes["generator"].calls[1][0].content
    assert "misuse of aggregate function" in retry_prompt
    assert state["query_result"]["rows"] == [[1000]]


def test_clarifying_question_ends_the_turn_without_sql(use_fakes):
    fakes = use_fakes(
        classifier=classified("generate_sql"),
        generator=FakeLLM(SQLGeneration(plan="too vague", sql=None, clarification="Best by revenue or by units sold?")),
    )

    state = ask("Show the best")

    assert state["messages"][-1].content == "Best by revenue or by units sold?"
    assert state["generated_sql"] is None
    assert fakes["explainer"].calls == []


def test_schema_question_is_answered_from_the_schema(use_fakes):
    fakes = use_fakes(classifier=classified("schema_info"), explainer=FakeLLM("There are seven tables."))

    state = ask("What tables do you have?")

    assert state["messages"][-1].content == "There are seven tables."
    assert "CREATE TABLE customers" in fakes["explainer"].calls[0][0].content


def test_explaining_a_broken_query_passes_the_validator_findings(use_fakes):
    fakes = use_fakes(
        classifier=classified("explain_sql", user_sql="SELECT * FROM employee"),
        explainer=FakeLLM("It reads a table that does not exist."),
    )

    ask("Explain this: SELECT * FROM employee")

    assert "Unknown table 'employee'" in fakes["explainer"].calls[0][0].content


def test_debug_shows_a_validated_fix(use_fakes):
    use_fakes(
        classifier=classified("debug_sql", user_sql="SELECT nme FROM products"),
        debugger=FakeLLM(
            SQLDebugResult(issue="Typo in column name.", explanation="It is called name.", corrected_sql="SELECT name FROM products")
        ),
    )

    state = ask("Why does this fail? SELECT nme FROM products")

    assert "**Issue:** Typo in column name." in state["messages"][-1].content
    assert "SELECT name FROM products" in state["messages"][-1].content
    assert state["generated_sql"] == "SELECT name FROM products"


def test_debug_never_shows_a_fix_that_fails_validation(use_fakes):
    use_fakes(
        classifier=classified("debug_sql", user_sql="SELECT nme FROM products"),
        debugger=FakeLLM(SQLDebugResult(issue="Typo.", explanation="Wrong name.", corrected_sql="SELECT title FROM products")),
    )

    state = ask("Why does this fail? SELECT nme FROM products")

    assert "couldn't produce a corrected query" in state["messages"][-1].content
    assert "SELECT title" not in state["messages"][-1].content
    assert state["generated_sql"] is None


def test_optimize_refuses_invalid_sql_without_calling_the_llm(use_fakes):
    fakes = use_fakes(classifier=classified("optimize_sql", user_sql="SELECT * FROM employee"))

    state = ask("Make this faster: SELECT * FROM employee")

    assert "problems that need fixing" in state["messages"][-1].content
    assert fakes["optimizer"].calls == []


@pytest.mark.parametrize(
    ("optimized_sql", "expected_note"),
    [
        ("SELECT first_name FROM customers WHERE state IN ('CA')", "Checked: it returns the same rows"),
        ("SELECT first_name FROM customers WHERE state = 'NY'", "Warning: it does not return the same rows"),
    ],
)
def test_optimize_compares_the_results_of_both_queries(use_fakes, optimized_sql, expected_note):
    original = "SELECT first_name FROM customers WHERE state = 'CA'"
    use_fakes(
        classifier=classified("optimize_sql", user_sql=original),
        optimizer=FakeLLM(SQLOptimization(changes=["Tidied up."], index_suggestions=[], optimized_sql=optimized_sql)),
    )

    state = ask(f"Optimize: {original}")

    assert expected_note in state["messages"][-1].content
    assert "**Estimated cost:** Low (reads about 200 rows)" in state["messages"][-1].content


def test_conversation_memory_is_kept_per_thread(use_fakes):
    use_fakes(classifier=classified("schema_info"), explainer=FakeLLM("Answer."))
    thread = str(uuid.uuid4())

    ask("First question", thread)
    second = ask("Second question", thread)
    other_thread = ask("Different conversation")

    assert [m.content for m in second["messages"]] == ["First question", "Answer.", "Second question", "Answer."]
    assert len(other_thread["messages"]) == 2


def test_each_turn_starts_with_clean_per_question_fields(use_fakes):
    use_fakes(classifier=classified("generate_sql"), generator=generated("SELECT nme FROM products"))
    thread = str(uuid.uuid4())
    ask("Product names", thread)

    use_fakes(classifier=classified("generate_sql"), generator=generated(VALID_SQL), explainer=FakeLLM("Six."))
    state = ask("List the categories", thread)

    assert state["validation_errors"] == []
    assert state["retry_count"] == 0
    assert state["query_result"]["row_count"] == 6


def test_long_conversations_send_only_recent_messages_to_the_llm(use_fakes):
    fakes = use_fakes(classifier=classified("schema_info"), explainer=FakeLLM("Answer."))
    thread = str(uuid.uuid4())

    for turn in range(7):
        state = ask(f"Question {turn}", thread)

    sent = fakes["classifier"].calls[-1][1:]
    assert len(state["messages"]) == 14
    assert len(sent) <= 10
    assert sent[0].content == "Question 2"
    assert sent[-1].content == "Question 6"
