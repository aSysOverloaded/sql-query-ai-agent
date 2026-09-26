"""
FastAPI server: exposes the SQL agent to the frontend.

Run from the backend folder:
    uvicorn app.main:app --reload
"""

import json
import logging
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, StringConstraints

from app import config
from app.agent.graph import agent
from app.agent.llm import RATE_LIMIT_ERRORS
from app.db.database import get_schema

logger = logging.getLogger(__name__)

BUSY_MESSAGE = "The AI service is busy right now. Please try again in a moment."
ERROR_MESSAGE = "Something went wrong while answering. Please try again."

STEP_LABELS = {
    "classify_intent": "Understanding your question…",
    "generate_sql": "Writing SQL…",
    "validate_query": "Validating the SQL…",
    "execute_query": "Running the query…",
    "explain": "Explaining the results…",
    "answer_schema_question": "Looking at the database schema…",
    "explain_user_sql": "Explaining…",
    "debug_user_sql": "Debugging your query…",
    "optimize_user_sql": "Optimizing your query…",
    "refuse": "Preparing a reply…",
    "give_up": "Preparing a reply…",
}

UserMessage = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=config.MAX_MESSAGE_LENGTH)
]
ThreadId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ChatRequest(BaseModel):
    message: UserMessage
    thread_id: ThreadId


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


class QueryCost(BaseModel):
    level: str
    rows_scanned: int
    notes: list[str]
    plan: list[str]


class ChatResponse(BaseModel):
    thread_id: str
    intent: str | None
    reply: str
    sql: str | None
    explanation: str | None
    warnings: list[str]
    result: QueryResult | None
    cost: QueryCost | None


app = FastAPI(
    title="SQL Query AI Agent",
    description="Turns natural-language questions into validated, read-only SQL.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def build_response(thread_id: str, state: dict) -> ChatResponse:
    """Map the agent's final state to the fields each UI panel needs."""
    gave_up = bool(state.get("validation_errors"))
    return ChatResponse(
        thread_id=thread_id,
        intent=state.get("intent"),
        reply=state["messages"][-1].text,
        sql=None if gave_up else state.get("generated_sql"),
        explanation=state.get("explanation"),
        warnings=state.get("validation_warnings") or [],
        result=state.get("query_result"),
        cost=None if gave_up else state.get("query_cost"),
    )


def thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


@app.post("/api/chat")
def chat(request: ChatRequest) -> ChatResponse:
    try:
        state = agent.invoke(
            {"messages": [HumanMessage(request.message)]}, config=thread_config(request.thread_id)
        )
    except RATE_LIMIT_ERRORS:
        logger.warning("LLM rate limit reached", exc_info=True)
        raise HTTPException(status_code=503, detail=BUSY_MESSAGE)
    except Exception:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGE)
    return build_response(request.thread_id, state)


def sse_event(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_agent(request: ChatRequest) -> Iterator[str]:
    """Yield a progress event as each node starts, then the final result (or an error)."""
    run_config = thread_config(request.thread_id)
    try:
        for task in agent.stream(
            {"messages": [HumanMessage(request.message)]}, config=run_config, stream_mode="tasks"
        ):
            if "input" in task:
                label = STEP_LABELS.get(task["name"], "Working…")
                yield sse_event("progress", {"step": task["name"], "label": label})
        state = agent.get_state(run_config).values
        yield sse_event("result", build_response(request.thread_id, state).model_dump(mode="json"))
    except RATE_LIMIT_ERRORS:
        logger.warning("LLM rate limit reached", exc_info=True)
        yield sse_event("error", {"detail": BUSY_MESSAGE})
    except Exception:
        logger.exception("Agent failed")
        yield sse_event("error", {"detail": ERROR_MESSAGE})


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_agent(request), media_type="text/event-stream")


@app.get("/api/schema")
def schema() -> dict[str, dict]:
    return get_schema()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
