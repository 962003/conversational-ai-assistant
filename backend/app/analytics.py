"""Analytics aggregation — usage, resolution/fallback rates, and business outcomes.

Built for the questions a solution consultant asks ("how much work did this deflect,
and what did it save?"), not just raw chatbot logs.
"""
from .config import get_settings
from .database import get_conn

INTENT_DISPLAY = {
    "order_status": "Order Status",
    "refund_policy": "Refund Policy",
    "pricing": "Pricing",
    "product_information": "Product Information",
    "human_agent": "Human Agent",
    "general_question": "General Question",
}


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def get_analytics() -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute(
            """SELECT
                 COUNT(*)                              AS total_turns,
                 COUNT(DISTINCT session_id)            AS total_sessions,
                 SUM(kb_hit)                           AS kb_hits,
                 SUM(escalated)                        AS escalated_turns,
                 SUM(is_fallback)                      AS fallback_turns,
                 AVG(CASE WHEN escalated = 0 THEN confidence END) AS avg_conf
               FROM conversations"""
        ).fetchone()

        escalated_sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) c FROM conversations WHERE escalated = 1"
        ).fetchone()["c"]

        intent_rows = conn.execute(
            """SELECT intent, COUNT(*) c FROM conversations
               WHERE intent IS NOT NULL GROUP BY intent ORDER BY c DESC"""
        ).fetchall()

        sentiment_rows = conn.execute(
            """SELECT sentiment, COUNT(*) c FROM conversations
               WHERE sentiment IS NOT NULL GROUP BY sentiment"""
        ).fetchall()

        usage_rows = conn.execute(
            """SELECT date(created_at) d, COUNT(*) c
               FROM conversations GROUP BY date(created_at)
               ORDER BY d DESC LIMIT 7"""
        ).fetchall()

        recent = conn.execute(
            """SELECT session_id, user_message, intent, escalated, confidence,
                      is_fallback, created_at
               FROM conversations ORDER BY id DESC LIMIT 10"""
        ).fetchall()

        tickets_total = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
        open_tickets = conn.execute(
            "SELECT COUNT(*) c FROM tickets WHERE status = 'open'"
        ).fetchone()["c"]
        ticket_rows = conn.execute(
            """SELECT id, name, email, issue, status, created_at
               FROM tickets ORDER BY id DESC LIMIT 10"""
        ).fetchall()

    total_turns = row["total_turns"] or 0
    total_sessions = row["total_sessions"] or 0
    kb_hits = row["kb_hits"] or 0
    escalated_turns = row["escalated_turns"] or 0
    fallback_turns = row["fallback_turns"] or 0
    avg_conf = round(row["avg_conf"], 3) if row["avg_conf"] is not None else 0.0
    resolved_sessions = max(total_sessions - escalated_sessions, 0)

    # Top intents
    intent_total = sum(r["c"] for r in intent_rows) or 1
    top_intents = [
        {
            "intent": INTENT_DISPLAY.get(r["intent"], r["intent"]),
            "count": r["c"],
            "percent": _pct(r["c"], intent_total),
        }
        for r in intent_rows
    ]

    # Business outcomes — value of deflected human contacts.
    deflected = resolved_sessions
    cost_saved = round(deflected * settings.cost_per_human_contact_usd, 2)
    hours_saved = round(deflected * settings.minutes_per_human_contact / 60.0, 1)

    return {
        # --- Usage ---
        "total_conversations": total_sessions,
        "total_turns": total_turns,
        "avg_turns_per_conversation": round(total_turns / total_sessions, 1) if total_sessions else 0.0,
        "usage_by_day": [{"date": r["d"], "turns": r["c"]} for r in reversed(usage_rows)],
        # --- Resolution & quality ---
        "resolved_conversations": resolved_sessions,
        "resolution_rate": _pct(resolved_sessions, total_sessions),   # session containment
        "escalations": escalated_sessions,
        "escalation_rate": _pct(escalated_sessions, total_sessions),
        "fallback_rate": _pct(fallback_turns, total_turns),           # turns the bot couldn't answer
        "knowledge_base_hits": kb_hits,
        "kb_hit_rate": _pct(kb_hits, total_turns),
        "avg_confidence": avg_conf,
        # --- Business outcomes ---
        "business_outcomes": {
            "contacts_deflected": deflected,
            "estimated_cost_saved_usd": cost_saved,
            "estimated_hours_saved": hours_saved,
            "assumptions": {
                "cost_per_human_contact_usd": settings.cost_per_human_contact_usd,
                "minutes_per_human_contact": settings.minutes_per_human_contact,
            },
        },
        # --- Breakdowns ---
        "top_intents": top_intents,
        "sentiment": {r["sentiment"]: r["c"] for r in sentiment_rows},
        # --- Escalation queue (Bot → Agent handoff) ---
        "tickets_created": tickets_total,
        "open_tickets": open_tickets,
        "escalation_queue": [dict(r) for r in ticket_rows],
        # --- Activity ---
        "recent_messages": [dict(r) for r in recent],
        # Back-compat alias
        "containment_rate": _pct(resolved_sessions, total_sessions),
    }
