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


class SQLGeneration(BaseModel):
    """A SQLite query answering the user's request, or a clarifying question if that is impossible."""

    plan: str = Field(
        description="Briefly: which tables, joins and filters answer the request, and any assumptions made."
    )
    sql: str | None = Field(
        default=None,
        description="One read-only SQLite SELECT query. Null only if a clarifying question is needed.",
    )
    clarification: str | None = Field(
        default=None,
        description="A short question for the user, only when the request cannot be answered with a reasonable assumption.",
    )


class SQLDebugResult(BaseModel):
    """Diagnosis of a broken SQL query and a corrected version."""

    issue: str = Field(description="One sentence naming what is wrong with the query.")
    explanation: str = Field(description="Why it is wrong, in simple English for someone learning SQL.")
    corrected_sql: str = Field(description="The fixed, read-only SQLite query.")


class SQLOptimization(BaseModel):
    """A cleaner, faster version of a working SQL query."""

    changes: list[str] = Field(
        description="Each improvement made, one short sentence each (readability, performance, removed joins)."
    )
    index_suggestions: list[str] = Field(
        description="CREATE INDEX statements that would help this query. Empty if none would help."
    )
    optimized_sql: str = Field(
        description="The improved read-only SQLite query. It must return exactly the same results as the original."
    )


class AgentState(TypedDict):
    """Shared data that every node in the graph reads from and writes to."""

    messages: Annotated[list[AnyMessage], add_messages]
    intent: Intent | None
    user_sql: str | None
    generated_sql: str | None
    generation_plan: str | None
    validation_errors: list[str]
    validation_warnings: list[str]
    retry_count: int
    query_result: dict | None
    query_cost: dict | None
    explanation: str | None
