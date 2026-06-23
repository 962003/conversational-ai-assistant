"""Analytics aggregation over the conversations table."""
from .database import get_conn

INTENT_DISPLAY = {
    "order_status": "Order Status",
    "refund_policy": "Refund Policy",
    "pricing": "Pricing",
    "product_information": "Product Information",
    "human_agent": "Human Agent",
    "general_question": "General Question",
}


def get_analytics() -> dict:
    with get_conn() as conn:
        total_turns = conn.execute("SELECT COUNT(*) c FROM conversations").fetchone()["c"]
        total_sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) c FROM conversations"
        ).fetchone()["c"]
        escalations = conn.execute(
            "SELECT COUNT(*) c FROM conversations WHERE escalated = 1"
        ).fetchone()["c"]
        kb_hits = conn.execute(
            "SELECT COUNT(*) c FROM conversations WHERE kb_hit = 1"
        ).fetchone()["c"]
        tickets = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]

        intent_rows = conn.execute(
            """SELECT intent, COUNT(*) c FROM conversations
               WHERE intent IS NOT NULL GROUP BY intent ORDER BY c DESC"""
        ).fetchall()

        sentiment_rows = conn.execute(
            """SELECT sentiment, COUNT(*) c FROM conversations
               WHERE sentiment IS NOT NULL GROUP BY sentiment"""
        ).fetchall()

        recent = conn.execute(
            """SELECT session_id, user_message, intent, escalated, created_at
               FROM conversations ORDER BY id DESC LIMIT 10"""
        ).fetchall()

    # Resolved = sessions that were never escalated
    escalated_sessions = 0
    if total_sessions:
        with get_conn() as conn:
            escalated_sessions = conn.execute(
                "SELECT COUNT(DISTINCT session_id) c FROM conversations WHERE escalated = 1"
            ).fetchone()["c"]
    resolved_sessions = max(total_sessions - escalated_sessions, 0)

    top_intents = []
    intent_total = sum(r["c"] for r in intent_rows) or 1
    for r in intent_rows:
        top_intents.append(
            {
                "intent": INTENT_DISPLAY.get(r["intent"], r["intent"]),
                "count": r["c"],
                "percent": round(100 * r["c"] / intent_total, 1),
            }
        )

    containment_rate = round(100 * resolved_sessions / total_sessions, 1) if total_sessions else 0.0
    kb_hit_rate = round(100 * kb_hits / total_turns, 1) if total_turns else 0.0

    return {
        "total_conversations": total_sessions,
        "total_turns": total_turns,
        "resolved_conversations": resolved_sessions,
        "escalations": escalated_sessions,
        "containment_rate": containment_rate,
        "knowledge_base_hits": kb_hits,
        "kb_hit_rate": kb_hit_rate,
        "tickets_created": tickets,
        "top_intents": top_intents,
        "sentiment": {r["sentiment"]: r["c"] for r in sentiment_rows},
        "recent_messages": [dict(r) for r in recent],
    }
