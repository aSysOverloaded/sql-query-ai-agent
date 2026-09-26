"""
Wires the nodes into a LangGraph workflow.
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app import config
from app.agent.nodes import (
    answer_schema_question,
    classify_intent,
    debug_user_sql,
    execute_query,
    explain,
    explain_user_sql,
    generate_sql,
    give_up,
    optimize_user_sql,
    refuse,
    validate_query,
)
from app.agent.state import AgentState

INTENT_TO_NODE = {
    "generate_sql": "generate_sql",
    "explain_sql": "explain_user_sql",
    "optimize_sql": "optimize_user_sql",
    "debug_sql": "debug_user_sql",
    "schema_info": "answer_schema_question",
    "destructive": "refuse",
    "out_of_scope": "refuse",
}


def route_after_classification(state: AgentState) -> str:
    """Choose the next node based on the detected intent."""
    return INTENT_TO_NODE[state["intent"]]


def route_after_generation(state: AgentState) -> str:
    """No SQL means the generator asked a clarifying question, so the turn ends there."""
    if state["generated_sql"] is None:
        return END
    return "validate_query"


def retry_or_give_up(state: AgentState) -> str:
    """After a failure, try generating again until MAX_SQL_RETRIES is used up."""
    if state["retry_count"] <= config.MAX_SQL_RETRIES:
        return "generate_sql"
    return "give_up"


def route_after_validation(state: AgentState) -> str:
    if state["validation_errors"]:
        return retry_or_give_up(state)
    return "execute_query"


def route_after_execution(state: AgentState) -> str:
    if state["validation_errors"]:
        return retry_or_give_up(state)
    return "explain"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("refuse", refuse)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_query", validate_query)
    graph.add_node("execute_query", execute_query)
    graph.add_node("explain", explain)
    graph.add_node("give_up", give_up)
    graph.add_node("answer_schema_question", answer_schema_question)
    graph.add_node("explain_user_sql", explain_user_sql)
    graph.add_node("debug_user_sql", debug_user_sql)
    graph.add_node("optimize_user_sql", optimize_user_sql)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent", route_after_classification, sorted(set(INTENT_TO_NODE.values()))
    )
    graph.add_conditional_edges("generate_sql", route_after_generation, ["validate_query", END])
    graph.add_conditional_edges(
        "validate_query", route_after_validation, ["execute_query", "generate_sql", "give_up"]
    )
    graph.add_conditional_edges(
        "execute_query", route_after_execution, ["explain", "generate_sql", "give_up"]
    )

    for final_node in [
        "explain",
        "give_up",
        "refuse",
        "answer_schema_question",
        "explain_user_sql",
        "debug_user_sql",
        "optimize_user_sql",
    ]:
        graph.add_edge(final_node, END)

    return graph.compile(checkpointer=InMemorySaver())


agent = build_graph()
