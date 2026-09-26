"""
Central settings. The API key comes from backend/.env; everything else has a default here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

DEFAULT_MODELS = {
    "groq": {
        "classifier": "openai/gpt-oss-20b",
        "generator": "openai/gpt-oss-120b",
        "explainer": "openai/gpt-oss-20b",
    },
    "gemini": {
        "classifier": "gemini-3.5-flash-lite",
        "generator": "gemini-3.5-flash",
        "explainer": "gemini-3.5-flash-lite",
    },
}
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", DEFAULT_MODELS[LLM_PROVIDER]["classifier"])
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", DEFAULT_MODELS[LLM_PROVIDER]["generator"])
EXPLAINER_MODEL = os.getenv("EXPLAINER_MODEL", DEFAULT_MODELS[LLM_PROVIDER]["explainer"])

DB_DIR = BACKEND_DIR / "app" / "db"
DB_PATH = DB_DIR / "company.db"
SCHEMA_PATH = DB_DIR / "schema.sql"

MAX_SQL_RETRIES = 2
MAX_HISTORY_MESSAGES = 10
LLM_TIMEOUT_SECONDS = 60

MAX_MESSAGE_LENGTH = 2000
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
