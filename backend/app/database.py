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
            """
        )


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
) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO conversations
               (session_id, user_message, bot_response, intent, kb_hit, source, escalated, sentiment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                user_message,
                bot_response,
                intent,
                1 if kb_hit else 0,
                source,
                1 if escalated else 0,
                sentiment,
            ),
        )


def create_ticket(session_id: str, name: str, email: str, issue: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (session_id, name, email, issue) VALUES (?, ?, ?, ?)",
            (session_id, name, email, issue),
        )
        return cur.lastrowid
