"""
Tests for the demo rate limiter. Time is simulated with monkeypatch, so nothing actually waits.
"""

import uuid

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import rate_limit
from app.agent.state import IntentClassification
from app.main import app
from app.rate_limit import RateLimiter, client_ip
from tests.conftest import FakeLLM


def fake_clock(monkeypatch, start=1000.0):
    clock = {"now": start}
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock["now"])
    return clock


def request_with(headers=None, host="10.0.0.1"):
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (host, 1234),
    }
    return Request(scope)


def test_allows_requests_up_to_the_hourly_limit(monkeypatch):
    fake_clock(monkeypatch)
    limiter = RateLimiter(per_hour=3, per_day=100)
    assert [limiter.check("a") for _ in range(3)] == [None, None, None]
    assert "3 questions per hour" in limiter.check("a")


def test_each_visitor_has_their_own_hourly_limit(monkeypatch):
    fake_clock(monkeypatch)
    limiter = RateLimiter(per_hour=1, per_day=100)
    assert limiter.check("a") is None
    assert limiter.check("a") is not None
    assert limiter.check("b") is None


def test_hourly_limit_resets_after_an_hour(monkeypatch):
    clock = fake_clock(monkeypatch)
    limiter = RateLimiter(per_hour=1, per_day=100)
    limiter.check("a")
    assert limiter.check("a") is not None
    clock["now"] += rate_limit.HOUR_SECONDS + 1
    assert limiter.check("a") is None


def test_daily_limit_applies_across_all_visitors(monkeypatch):
    clock = fake_clock(monkeypatch)
    limiter = RateLimiter(per_hour=100, per_day=2)
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert "daily question limit" in limiter.check("c")
    clock["now"] += rate_limit.DAY_SECONDS + 1
    assert limiter.check("c") is None


def test_rejected_requests_are_not_counted(monkeypatch):
    fake_clock(monkeypatch)
    limiter = RateLimiter(per_hour=1, per_day=2)
    limiter.check("a")
    limiter.check("a")
    limiter.check("a")
    assert limiter.check("b") is None


def test_client_ip_uses_the_proxy_header_when_present():
    assert client_ip(request_with({"X-Forwarded-For": "203.0.113.7, 10.1.1.1"})) == "203.0.113.7"
    assert client_ip(request_with()) == "10.0.0.1"


def test_api_returns_429_before_calling_the_llm(use_fakes, fresh_rate_limiter):
    fresh_rate_limiter.per_hour = 1
    fakes = use_fakes(classifier=FakeLLM(IntentClassification(reason="t", intent="out_of_scope")))
    client = TestClient(app)
    body = {"message": "hello", "thread_id": str(uuid.uuid4())}

    assert client.post("/api/chat", json=body).status_code == 200
    blocked = client.post("/api/chat/stream", json=body)

    assert blocked.status_code == 429
    assert blocked.json()["detail"].startswith("You've reached the limit of 1 question per hour")
    assert len(fakes["classifier"].calls) == 1
