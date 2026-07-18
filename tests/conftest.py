from __future__ import annotations

import os

import pytest

# Force a throwaway sqlite file for the test run so tests never touch a real
# dev database and are safe to re-run (plan §4.1 fallback path).
os.environ["DATABASE_URL"] = "sqlite:///./data/test_negotiator.db"

from app.db import Base, engine  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _init_test_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)
    yield
