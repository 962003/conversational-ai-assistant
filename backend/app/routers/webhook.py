"""Dialogflow CX webhook fulfillment endpoint.

Dialogflow CX calls this with a WebhookRequest payload. We extract the user text,
the matched intent, and any session parameters, run the same KB+Gemini pipeline,
and return a WebhookResponse with the grounded answer plus session parameters.

Request/response schema:
https://cloud.google.com/dialogflow/cx/docs/reference/rest/v3/WebhookRequest
"""
import re

from fastapi import APIRouter, Header, HTTPException, Request

from ..config import get_settings
from .. import database, service

router = APIRouter(prefix="/dialogflow", tags=["dialogflow"])

# Map Dialogflow CX intent display names to internal intent keys.
_KNOWN_INTENTS = {
    "order_status", "refund_policy", "pricing",
    "product_information", "human_agent", "general_question",
}


def _normalize_intent(display_name: str | None) -> str | None:
    if not display_name:
        return None
    key = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
    # tolerate names like "order.status", "Refund Policy", "human.agent"
    aliases = {
        "order_status": "order_status",
        "track_order": "order_status",
        "refund_policy": "refund_policy",
        "refund": "refund_policy",
        "pricing": "pricing",
        "price": "pricing",
        "product_information": "product_information",
        "product_info": "product_information",
        "human_agent": "human_agent",
        "talk_to_agent": "human_agent",
        "live_agent": "human_agent",
        "general_question": "general_question",
        "default_welcome_intent": "general_question",
    }
    if key in _KNOWN_INTENTS:
        return key
    return aliases.get(key)


def _extract_text(body: dict) -> str:
    # CX sends the end-user text in `text` (typed) or `transcript` (speech).
    return (body.get("text") or body.get("transcript") or "").strip()


@router.post("/webhook")
async def cx_webhook(
    request: Request,
    x_webhook_secret: str | None = Header(default=None),
):
    settings = get_settings()
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    body = await request.json()

    text = _extract_text(body)
    intent_info = body.get("intentInfo") or {}
    intent = _normalize_intent(intent_info.get("displayName"))
    session_info = body.get("sessionInfo") or {}
    session_path = session_info.get("session", "")
    session_id = session_path.split("/")[-1] if session_path else "cx-session"
    tag = (body.get("fulfillmentInfo") or {}).get("tag", "")

    # Human handoff fulfillment: collect ticket from session parameters.
    if tag == "create_ticket" or intent == "human_agent":
        params = session_info.get("parameters", {}) or {}
        name = params.get("person_name") or params.get("name")
        email = params.get("email")
        issue = params.get("issue") or text
        if name and email:
            ticket_id = database.create_ticket(session_id, name, email, issue or "")
            msg = (
                f"Thanks {name}! Ticket #{ticket_id} has been created and a human "
                f"agent will email you at {email}."
            )
            database.log_turn(session_id, text, msg, "human_agent", False, None, True)
            return _cx_response(msg, {"ticket_id": ticket_id})
        return _cx_response(service.HUMAN_HANDOFF_MESSAGE, {})

    if not text:
        return _cx_response(
            "Sorry, I didn't catch that. Could you rephrase your question?", {}
        )

    result = service.handle_turn(text, session_id, intent=intent)
    sources = [s["doc"] for s in result.get("sources", [])]
    params_out = {
        "detected_intent": result["intent"],
        "kb_hit": result["kb_hit"],
        "sentiment": result["sentiment"],
        "confidence": result["confidence"],
        "confidence_label": result["confidence_label"],
        "sources": ", ".join(dict.fromkeys(sources)) or "none",
    }
    return _cx_response(result["response"], params_out, sources=result.get("sources", []),
                        confidence=result["confidence"])


def _cx_response(message: str, parameters: dict, sources: list | None = None,
                 confidence: float | None = None) -> dict:
    """Build a Dialogflow CX WebhookResponse.

    Returns the answer as a text message, plus a structured custom payload
    carrying the grounded sources and confidence (Phase 2 contract:
    answer + sources + confidence) that a CX agent or chat client can render.
    """
    messages: list[dict] = [{"text": {"text": [message]}}]
    if sources:
        messages.append({
            "payload": {
                "answer": message,
                "confidence": confidence,
                "sources": [
                    {"doc": s["doc"], "title": s["title"], "score": s["score"]}
                    for s in sources
                ],
            }
        })
    return {
        "fulfillmentResponse": {"messages": messages},
        "sessionInfo": {"parameters": parameters},
    }
