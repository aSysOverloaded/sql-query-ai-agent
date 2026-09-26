"""
API tests using FastAPI's in-process TestClient and fake LLMs: no server and no API calls needed.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.exceptions import ModelRateLimitError

from app.agent.prompts import OUT_OF_SCOPE_MESSAGE
from app.agent.state import IntentClassification, SQLGeneration
from app.main import BUSY_MESSAGE, ERROR_MESSAGE, app
from tests.conftest import FakeLLM

client = TestClient(app)

VALID_SQL = "SELECT name FROM categories ORDER BY name"


def chat(message, path="/api/chat"):
    return client.post(path, json={"message": message, "thread_id": str(uuid.uuid4())})


def sql_answer_fakes(*sqls):
    return {
        "classifier": FakeLLM(IntentClassification(reason="test", intent="generate_sql")),
        "generator": FakeLLM(*[SQLGeneration(plan="test plan", sql=sql) for sql in sqls]),
        "explainer": FakeLLM("There are six categories."),
    }


def parse_sse(body):
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_schema_lists_all_tables(seeded_database):
    schema = client.get("/api/schema").json()
    assert len(schema) == 7
    assert "hire_date" in schema["employees"]["columns"]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"message": "   ", "thread_id": "t1"}, "message"),
        ({"message": "x" * 2001, "thread_id": "t1"}, "message"),
        ({"message": "hello"}, "thread_id"),
    ],
)
def test_invalid_requests_are_rejected_with_422(use_fakes, body, field):
    fakes = use_fakes()
    response = client.post("/api/chat", json=body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert fakes["classifier"].calls == []


def test_sql_answer_fills_every_panel_field(use_fakes):
    use_fakes(**sql_answer_fakes(VALID_SQL))

    body = chat("List the categories").json()

    assert body["intent"] == "generate_sql"
    assert body["sql"] == VALID_SQL
    assert body["explanation"] == "There are six categories."
    assert body["warnings"] == []
    assert body["result"]["columns"] == ["name"]
    assert body["result"]["row_count"] == 6
    assert body["reply"].startswith("```sql")


def test_refusal_has_no_sql_or_results(use_fakes):
    use_fakes(classifier=FakeLLM(IntentClassification(reason="test", intent="out_of_scope")))

    body = chat("Who won the World Cup?").json()

    assert body["intent"] == "out_of_scope"
    assert body["reply"] == OUT_OF_SCOPE_MESSAGE
    assert body["sql"] is None
    assert body["result"] is None


def test_sql_is_hidden_when_the_agent_gives_up(use_fakes):
    use_fakes(**sql_answer_fakes("SELECT nme FROM products"))

    body = chat("Product names").json()

    assert body["sql"] is None
    assert body["result"] is None


def test_rate_limit_returns_503_with_a_friendly_message(use_fakes):
    use_fakes(classifier=FakeLLM(ModelRateLimitError("429 Too Many Requests")))

    response = chat("List the categories")

    assert response.status_code == 503
    assert response.json() == {"detail": BUSY_MESSAGE}


def test_unexpected_error_returns_500_without_internal_details(use_fakes):
    use_fakes(classifier=FakeLLM(RuntimeError("secret internal stack detail")))

    response = chat("List the categories")

    assert response.status_code == 500
    assert response.json() == {"detail": ERROR_MESSAGE}
    assert "secret" not in response.text


def test_stream_sends_progress_then_the_result(use_fakes):
    use_fakes(**sql_answer_fakes("SELECT nme FROM products", VALID_SQL))

    response = chat("List the categories", path="/api/chat/stream")

    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    steps = [data["step"] for event, data in events if event == "progress"]
    assert steps == [
        "classify_intent",
        "generate_sql",
        "validate_query",
        "generate_sql",
        "validate_query",
        "execute_query",
        "explain",
    ]
    final_event, final_data = events[-1]
    assert final_event == "result"
    assert final_data["sql"] == VALID_SQL
    assert final_data["result"]["row_count"] == 6


def test_stream_reports_errors_as_an_event(use_fakes):
    use_fakes(classifier=FakeLLM(ModelRateLimitError("429 Too Many Requests")))

    events = parse_sse(chat("List the categories", path="/api/chat/stream").text)

    assert events[-1] == ("error", {"detail": BUSY_MESSAGE})


@pytest.mark.parametrize(
    ("origin", "allowed"), [("http://localhost:3000", True), ("http://evil.example", False)]
)
def test_cors_allows_only_the_frontend(origin, allowed):
    response = client.options(
        "/api/chat", headers={"Origin": origin, "Access-Control-Request-Method": "POST"}
    )
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed
