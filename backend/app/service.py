"""Core orchestration shared by the /chat and /dialogflow/webhook endpoints.

Pipeline:  message -> intent -> (human handoff?) -> KB retrieval -> Gemini grounding
-> persist analytics. This is the heart of the Contact Center AI flow.
"""
from . import database
from .config import get_settings
from .gemini_client import get_gemini
from .knowledge_base import get_kb


def _confidence(results: list[dict]) -> float:
    """Map the top retrieval score to a 0–1 confidence.

    Vector cosine scores are already ~0–1. Keyword (TF-IDF) scores are unbounded,
    so we squash them with x/(x+1). Returns 0.0 when nothing was retrieved.
    """
    if not results:
        return 0.0
    top = results[0]
    score = float(top.get("score", 0.0))
    if top.get("method") == "vector":
        return round(max(0.0, min(1.0, score)), 3)
    return round(score / (score + 1.0), 3)


def _confidence_label(confidence: float) -> str:
    threshold = get_settings().confidence_threshold
    if confidence >= max(0.7, threshold):
        return "high"
    if confidence >= threshold:
        return "medium"
    return "low"

# Which KB document each intent should bias retrieval toward (soft hint).
INTENT_DOC_HINT = {
    "refund_policy": "refund_policy.md",
    "pricing": "pricing.md",
    "order_status": "shipping.md",
    "product_information": "products.md",
}

HUMAN_HANDOFF_MESSAGE = (
    "I can connect you with a human agent. Could you share your **name**, "
    "**email**, and a short description of your **issue** so I can create a "
    "support ticket?"
)


def handle_turn(message: str, session_id: str, intent: str | None = None) -> dict:
    """Process one conversational turn and return a structured result.

    `intent` may be supplied by Dialogflow CX; if absent we detect it with Gemini.
    """
    gemini = get_gemini()
    kb = get_kb()

    detected_intent = intent or gemini.detect_intent(message)
    sentiment = gemini.detect_sentiment(message)

    # --- Human handoff branch ---
    if detected_intent == "human_agent":
        database.log_turn(
            session_id, message, HUMAN_HANDOFF_MESSAGE,
            intent="human_agent", kb_hit=False, source=None,
            escalated=True, sentiment=sentiment,
        )
        return {
            "response": HUMAN_HANDOFF_MESSAGE,
            "intent": "human_agent",
            "kb_hit": False,
            "escalated": True,
            "sentiment": sentiment,
            "confidence": 1.0,
            "confidence_label": "high",
            "sources": [],
            "session_id": session_id,
        }

    # --- Knowledge retrieval + grounded generation ---
    results = kb.search(message)

    # Re-rank: boost the chunk from the intent's expected document.
    hint = INTENT_DOC_HINT.get(detected_intent)
    if hint:
        results.sort(key=lambda r: (r["doc"] != hint, -r["score"]))

    kb_hit = bool(results)
    confidence = _confidence(results)
    label = _confidence_label(confidence)
    answer = gemini.generate_answer(message, results)
    source = results[0]["doc"] if results else None

    database.log_turn(
        session_id, message, answer,
        intent=detected_intent, kb_hit=kb_hit, source=source,
        escalated=False, sentiment=sentiment,
    )

    return {
        "response": answer,
        "intent": detected_intent,
        "kb_hit": kb_hit,
        "escalated": False,
        "sentiment": sentiment,
        "confidence": confidence,
        "confidence_label": label,
        "sources": [
            {
                "doc": r["doc"],
                "title": r["title"],
                "score": r["score"],
                "method": r.get("method"),
            }
            for r in results
        ],
        "session_id": session_id,
    }
