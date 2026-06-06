"""API integration tests for session routes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BREWMIND_OFFLINE", "true")
os.environ.setdefault("NEBIUS_API_KEY", "test-key")
os.environ.setdefault("NEBIUS_MODEL", "test-model")
os.environ.setdefault("NEBIUS_BASE_URL", "https://example.com/v1/")
os.environ.setdefault("MAX_REVISIONS", "5")

from mindbrew_v2.settings import get_settings

get_settings.cache_clear()

from api.main import app  # noqa: E402


def _noop_track(session_id: str, coro):
    task = MagicMock()
    task.cancel = MagicMock()
    return task


@pytest.fixture
def client(monkeypatch):
    import api.db.database as db_module

    db_module._engine = None
    db_module._SessionLocal = None
    get_settings.cache_clear()

    monkeypatch.setattr("api.routes.sessions._track_task", _noop_track)
    monkeypatch.setattr("api.routes.sessions.asyncio.create_task", lambda coro: _noop_track("", coro))
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_and_get_session(client: TestClient):
    res = client.post("/sessions", json={"raw_brief": "Produce wax esters from plant oil via fermentation."})
    assert res.status_code == 200
    body = res.json()
    session_id = body["id"]
    assert body["status"] == "running"
    assert body["raw_brief"].startswith("Produce wax esters")

    got = client.get(f"/sessions/{session_id}")
    assert got.status_code == 200
    assert got.json()["id"] == session_id


def test_delete_session(client: TestClient):
    created = client.post("/sessions", json={"raw_brief": "Temporary session for delete test."}).json()
    session_id = created["id"]

    deleted = client.delete(f"/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}

    missing = client.get(f"/sessions/{session_id}")
    assert missing.status_code == 404


def test_decide_rejects_when_session_not_awaiting_user(client: TestClient):
    created = client.post("/sessions", json={"raw_brief": "Brief for decide validation."}).json()
    session_id = created["id"]

    res = client.post(
        f"/sessions/{session_id}/steps/cp1_spec/decide",
        json={"action": "proceed"},
    )
    assert res.status_code == 409
    assert "awaiting_user" in res.json()["detail"]
