"""
Wires the nodes into a LangGraph workflow.
"""

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import classify_intent, not_implemented_yet, refuse
from app.agent.state import AgentState


def route_after_classification(state: AgentState) -> str:
    """Choose the next node based on the detected intent."""
    if state["intent"] in ("destructive", "out_of_scope"):
        return "refuse"
    return "not_implemented_yet"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("refuse", refuse)
    graph.add_node("not_implemented_yet", not_implemented_yet)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent", route_after_classification, ["refuse", "not_implemented_yet"]
    )
    graph.add_edge("refuse", END)
    graph.add_edge("not_implemented_yet", END)

    return graph.compile()


agent = build_graph()
