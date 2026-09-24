"""Session and transcript persistence, kept separate from HTTP routes."""

import json
import secrets
import sqlite3
from datetime import datetime, timezone


def now_iso() -> str:
    """Return a timezone-aware timestamp that JavaScript can parse."""
    return datetime.now(timezone.utc).isoformat()


def create_session(
    db: sqlite3.Connection,
    *,
    teacher_id: int | None = None,
    title: str = "Untitled Lecture",
) -> dict:
    """Create a unique lecture ID and optionally link it to its Teacher."""
    for _ in range(5):
        session_id = secrets.token_hex(8).upper()
        started_at = now_iso()
        try:
            db.execute(
                """
                INSERT INTO sessions (
                    session_id, teacher_id, title, start_time,
                    status, started_at
                )
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (session_id, teacher_id, title.strip() or "Untitled Lecture", started_at, started_at),
            )
            db.commit()
        except sqlite3.IntegrityError:
            # A primary-key collision is extremely unlikely. Retry rather than
            # risk returning a duplicate ID.
            db.rollback()
            continue

        return find_session(db, session_id)

    raise RuntimeError("Could not create a unique lecture session ID.")


def find_session(
    db: sqlite3.Connection,
    session_id: str,
) -> dict | None:
    row = db.execute(
        """
        SELECT session_id, teacher_id, title, start_time, end_time,
               status, started_at, ended_at
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    return dict(row) if row else None


def end_session(
    db: sqlite3.Connection,
    session_id: str,
) -> dict | None:
    """End a session. Calling this more than once keeps the original end time."""
    ended_at = now_iso()
    cursor = db.execute(
        """
        UPDATE sessions
        SET status = 'ended',
            end_time = COALESCE(end_time, ?),
            ended_at = COALESCE(ended_at, ?)
        WHERE session_id = ?
        """,
        (ended_at, ended_at, session_id),
    )
    db.commit()
    if cursor.rowcount == 0:
        return None
    return find_session(db, session_id)


def list_transcript(
    db: sqlite3.Connection,
    session_id: str,
) -> list[dict]:
    rows = db.execute(
        """
        SELECT id, session_id, text, created_at
        FROM transcripts
        WHERE session_id = ?
        ORDER BY id
        """,
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_transcript(
    db: sqlite3.Connection,
    session_id: str,
    text: str,
) -> dict | None:
    """Store a final speech result, or explain why it cannot be stored."""
    session = find_session(db, session_id)
    if session is None:
        return None
    if session["status"] != "active":
        return {"error": "This lecture has already ended."}

    created_at = now_iso()
    cursor = db.execute(
        """
        INSERT INTO transcripts (session_id, text, created_at)
        VALUES (?, ?, ?)
        """,
        (session_id, text, created_at),
    )
    db.commit()
    return {
        "id": cursor.lastrowid,
        "session_id": session_id,
        "text": text,
        "created_at": created_at,
    }


def create_conversation(
    db: sqlite3.Connection,
    session_id: str,
    conversation_id: str | None = None,
) -> dict:
    """Create a new conversation session-scoped to the given lecture."""
    cid = conversation_id or f"conv_{secrets.token_hex(6)}"
    created_at = now_iso()
    db.execute(
        """
        INSERT INTO conversations (id, session_id, created_at)
        VALUES (?, ?, ?)
        """,
        (cid, session_id, created_at),
    )
    db.commit()
    return {
        "id": cid,
        "session_id": session_id,
        "created_at": created_at,
    }


def find_conversation(
    db: sqlite3.Connection,
    conversation_id: str,
) -> dict | None:
    """Find a conversation by ID."""
    row = db.execute(
        """
        SELECT id, session_id, created_at
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,),
    ).fetchone()
    return dict(row) if row else None


def list_conversation_messages(
    db: sqlite3.Connection,
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    """Retrieve chronological messages for a conversation up to recent limit."""
    rows = db.execute(
        """
        SELECT id, conversation_id, role, content, sources, lecture_grounded, created_at
        FROM conversation_messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,),
    ).fetchall()
    messages = []
    for r in rows:
        try:
            sources = json.loads(r["sources"]) if r["sources"] else []
        except Exception:
            sources = []
        messages.append({
            "id": r["id"],
            "conversation_id": r["conversation_id"],
            "role": r["role"],
            "content": r["content"],
            "sources": sources,
            "lecture_grounded": bool(r["lecture_grounded"]),
            "created_at": r["created_at"],
        })
    if limit and len(messages) > limit:
        return messages[-limit:]
    return messages


def add_conversation_message(
    db: sqlite3.Connection,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[str] | None = None,
    lecture_grounded: bool = True,
) -> dict:
    """Record a user or assistant message against a conversation."""
    created_at = now_iso()
    sources_json = json.dumps(sources or [])
    grounded_int = 1 if lecture_grounded else 0
    cursor = db.execute(
        """
        INSERT INTO conversation_messages (conversation_id, role, content, sources, lecture_grounded, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, role, content, sources_json, grounded_int, created_at),
    )
    db.commit()
    return {
        "id": cursor.lastrowid,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "lecture_grounded": lecture_grounded,
        "created_at": created_at,
    }
