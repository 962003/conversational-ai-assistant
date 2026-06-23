"""Smoke tests — run without a Gemini API key (uses graceful fallbacks)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Using TestClient as a context manager triggers the lifespan
    # (init_db + KB warm-up) before any request runs.
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["kb_sections"] > 0


def test_knowledge_search_finds_refund(client):
    r = client.post("/knowledge/search", json={"query": "refund policy"})
    assert r.status_code == 200
    docs = [x["doc"] for x in r.json()["results"]]
    assert "refund_policy.md" in docs


def test_chat_pricing_intent(client):
    r = client.post("/chat", json={"message": "How much does the Pro plan cost?", "session_id": "t1"})
    body = r.json()
    assert r.status_code == 200
    assert body["intent"] == "pricing"
    assert body["kb_hit"] is True
    # Phase 2 contract: answer + sources + confidence
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["confidence_label"] in {"low", "medium", "high"}
    assert body["via"] == "direct"


def test_chat_unknown_question_low_confidence(client):
    r = client.post("/chat", json={"message": "asdfghjkl zxcvbnm qwerty?", "session_id": "tlow"})
    body = r.json()
    # No relevant KB match → no sources, zero confidence, low label.
    assert body["sources"] == []
    assert body["confidence"] == 0.0
    assert body["confidence_label"] == "low"


def test_human_handoff_escalates(client):
    r = client.post("/chat", json={"message": "I want to talk to a human", "session_id": "t2"})
    body = r.json()
    assert body["intent"] == "human_agent"
    assert body["escalated"] is True


def test_dialogflow_webhook_contract(client):
    payload = {
        "text": "What is your refund policy?",
        "intentInfo": {"displayName": "refund_policy"},
        "sessionInfo": {"session": "projects/p/locations/global/agents/a/sessions/demo"},
        "fulfillmentInfo": {"tag": "kb_search"},
    }
    r = client.post("/dialogflow/webhook", json=payload)
    assert r.status_code == 200
    body = r.json()
    msgs = body["fulfillmentResponse"]["messages"]
    assert msgs and msgs[0]["text"]["text"][0]
    # Webhook returns sources + confidence (as a custom payload + session params).
    payloads = [m["payload"] for m in msgs if "payload" in m]
    assert payloads and "sources" in payloads[0] and "confidence" in payloads[0]
    params = body["sessionInfo"]["parameters"]
    assert "confidence" in params and "sources" in params


def test_analytics_aggregates(client):
    client.post("/chat", json={"message": "pricing?", "session_id": "t3"})
    r = client.get("/analytics")
    assert r.status_code == 200
    a = r.json()
    assert a["total_turns"] >= 1
    # Consultant metrics present and well-formed.
    for key in ("resolution_rate", "fallback_rate", "escalation_rate", "kb_hit_rate"):
        assert 0.0 <= a[key] <= 100.0
    assert 0.0 <= a["avg_confidence"] <= 1.0
    bo = a["business_outcomes"]
    assert {"contacts_deflected", "estimated_cost_saved_usd", "estimated_hours_saved"} <= bo.keys()
    assert isinstance(a["usage_by_day"], list)


def test_fallback_rate_counts_unanswerable(client):
    client.post("/chat", json={"message": "zxqw nonsense gibberish?", "session_id": "tfb"})
    a = client.get("/analytics").json()
    assert a["fallback_rate"] > 0.0  # the gibberish turn is a fallback


def test_escalation_queue_lists_tickets(client):
    # Escalate, then create a ticket → it should appear in the queue.
    client.post("/chat", json={"message": "I want a human", "session_id": "tq"})
    tr = client.post("/ticket", json={
        "session_id": "tq", "name": "Asha", "email": "asha@example.com",
        "issue": "Refund not received",
    })
    assert tr.status_code == 200

    q = client.get("/tickets").json()
    assert q["total"] >= 1 and q["open"] >= 1
    assert any(t["email"] == "asha@example.com" for t in q["tickets"])

    a = client.get("/analytics").json()
    assert a["open_tickets"] >= 1
    assert any(t["name"] == "Asha" for t in a["escalation_queue"])
