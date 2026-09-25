"""Shared pytest fixtures use a temporary database for every test."""

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Keep automated tests deterministic and prevent any real provider calls.
os.environ["AI_PROVIDER"] = "heuristic"

from app import database  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    test_database = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_database)

    with TestClient(app) as test_client:
        yield test_client
