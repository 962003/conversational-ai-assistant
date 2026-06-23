"""Lightweight SQLite persistence for conversations and analytics events."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings

_lock = threading.Lock()


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    settings = get_settings()
    _ensure_parent(settings.database_path)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT,
                bot_response TEXT,
                intent TEXT,
                kb_hit INTEGER DEFAULT 0,
                source TEXT,
                escalated INTEGER DEFAULT 0,
                sentiment TEXT,
                confidence REAL DEFAULT 0,
                is_fallback INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                name TEXT,
                email TEXT,
                issue TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                rating INTEGER,          -- 1 = thumbs up (satisfied), 0 = thumbs down
                comment TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        # Migrate older databases that predate the new columns.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(conversations)")}
        if "confidence" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN confidence REAL DEFAULT 0")
        if "is_fallback" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN is_fallback INTEGER DEFAULT 0")


@contextmanager
def get_conn():
    settings = get_settings()
    _ensure_parent(settings.database_path)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        with _lock:
            yield conn
            conn.commit()
    finally:
        conn.close()


def log_turn(
    session_id: str,
    user_message: str,
    bot_response: str,
    intent: str | None,
    kb_hit: bool,
    source: str | None,
    escalated: bool = False,
    sentiment: str | None = None,
    confidence: float = 0.0,
    is_fallback: bool = False,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO conversations
               (session_id, user_message, bot_response, intent, kb_hit, source,
                escalated, sentiment, confidence, is_fallback)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                user_message,
                bot_response,
                intent,
                1 if kb_hit else 0,
                source,
                1 if escalated else 0,
                sentiment,
                float(confidence or 0.0),
                1 if is_fallback else 0,
            ),
        )


def create_ticket(session_id: str, name: str, email: str, issue: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (session_id, name, email, issue) VALUES (?, ?, ?, ?)",
            (session_id, name, email, issue),
        )
        return cur.lastrowid


def list_tickets(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, session_id, name, email, issue, status, created_at
               FROM tickets ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def log_feedback(session_id: str, rating: int, comment: str | None = None) -> int:
    """rating: 1 = thumbs up (satisfied), 0 = thumbs down. Drives CSAT."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO feedback (session_id, rating, comment) VALUES (?, ?, ?)",
            (session_id, 1 if rating else 0, comment),
        )
        return cur.lastrowid
