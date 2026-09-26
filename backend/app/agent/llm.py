"""
Creates chat models for the configured provider, so the rest of the agent never depends on one vendor.
"""

import groq
from langchain_core.exceptions import ModelRateLimitError
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app import config

RATE_LIMIT_ERRORS = (ModelRateLimitError, groq.RateLimitError)


def get_chat_model(model: str) -> BaseChatModel:
    """Return a deterministic (temperature 0) chat model from the provider set by LLM_PROVIDER."""
    if config.LLM_PROVIDER == "groq":
        return ChatGroq(model=model, temperature=0, timeout=config.LLM_TIMEOUT_SECONDS)
    if config.LLM_PROVIDER == "gemini":
        return ChatGoogleGenerativeAI(model=model, temperature=0, timeout=config.LLM_TIMEOUT_SECONDS)
    raise ValueError(f"Unknown LLM_PROVIDER '{config.LLM_PROVIDER}'. Use 'groq' or 'gemini'.")


def get_structured_model(model: str, schema: type[BaseModel]) -> Runnable:
    """A chat model whose output is forced to match the schema (JSON schema mode, not optional tool calls)."""
    return get_chat_model(model).with_structured_output(schema, method="json_schema")
