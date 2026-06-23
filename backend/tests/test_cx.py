"""Dialogflow CX endpoint tests (without a live agent → graceful 'not configured')."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_cx_status_reports_disabled_without_config(client):
    r = client.get("/cx/status")
    assert r.status_code == 200
    assert r.json()["cx_enabled"] is False


def test_cx_detect_intent_falls_back_when_unconfigured(client):
    r = client.post("/cx/detect-intent", json={"message": "hi", "session_id": "s"})
    assert r.status_code == 200
    body = r.json()
    assert body["cx_enabled"] is False
    assert "not configured" in body["message"].lower()


def test_health_exposes_cx_flag(client):
    r = client.get("/health")
    assert "dialogflow_cx_enabled" in r.json()
