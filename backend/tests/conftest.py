"""
Shared test setup. Dummy API keys let the agent modules import without real credentials;
tests replace every LLM with a fake, so no API call is ever made.
"""

import os

import pytest
from langchain_core.messages import AIMessage

from app.config import DB_PATH
from app.db.seed import build_database

os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")


@pytest.fixture(scope="session")
def seeded_database():
    """Make sure company.db exists (it is not committed to git) before tests that read it."""
    if not DB_PATH.exists():
        build_database()
    return DB_PATH


class FakeLLM:
    """Returns scripted outputs in order (repeating the last one) and records every call.
    A scripted exception is raised instead of returned, to simulate API failures."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        output = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(output, Exception):
            raise output
        return AIMessage(output) if isinstance(output, str) else output


@pytest.fixture
def use_fakes(monkeypatch, seeded_database):
    """Return a function that replaces every LLM in the agent with a fake; unnamed ones get a placeholder."""
    from app.agent import nodes

    def install(**fakes: FakeLLM) -> dict[str, FakeLLM]:
        roles = ["classifier", "generator", "explainer", "debugger", "optimizer"]
        installed = {role: fakes.get(role, FakeLLM("unused")) for role in roles}
        for role, fake in installed.items():
            monkeypatch.setattr(nodes, f"{role}_llm", fake)
        return installed

    return install
