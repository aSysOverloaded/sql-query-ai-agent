"""
Central settings. The API key comes from backend/.env; everything else has a default here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gemini-3.5-flash-lite")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemini-3.5-flash")

DB_DIR = BACKEND_DIR / "app" / "db"
DB_PATH = DB_DIR / "company.db"
SCHEMA_PATH = DB_DIR / "schema.sql"

MAX_SQL_RETRIES = 2
