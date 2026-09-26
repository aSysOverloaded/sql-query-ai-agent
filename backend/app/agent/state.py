"""
Data shapes shared by the agent: the graph state, the allowed intents and the classifier's output.
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

Intent = Literal[
    "generate_sql",
    "explain_sql",
    "optimize_sql",
    "debug_sql",
    "schema_info",
    "destructive",
    "out_of_scope",
]


class IntentClassification(BaseModel):
    """How the SQL assistant should handle the user's latest message."""

    reason: str = Field(description="One short sentence explaining which intent fits and why.")
    intent: Intent = Field(description="The single intent that best matches the user's latest message.")
    user_sql: str | None = Field(
        default=None,
        description="The SQL query included in the user's message, copied exactly. Null if there is none.",
    )


class AgentState(TypedDict):
    """Shared data that every node in the graph reads from and writes to."""

    messages: Annotated[list[AnyMessage], add_messages]
    intent: Intent | None
    user_sql: str | None
