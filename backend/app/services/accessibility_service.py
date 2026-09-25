"""Student-specific, lecture-scoped accessibility preference persistence."""

import sqlite3
from datetime import datetime, timezone


DEFAULT_MODE = "standard"
DEFAULT_TRANSLATION_LANGUAGE = "kn"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_preference(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
) -> dict | None:
    """Find one preference using the same composite key as the database."""
    row = db.execute(
        """
        SELECT student_id, session_id, mode, translation_language,
               created_at, updated_at
        FROM student_accessibility_preferences
        WHERE student_id = ? AND session_id = ?
        """,
        (student_id, session_id),
    ).fetchone()
    return dict(row) if row else None


def get_or_create_preference(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
) -> dict:
    """Return a saved preference, or create the per-session Standard default."""
    existing = find_preference(db, student_id=student_id, session_id=session_id)
    if existing is not None:
        return existing

    created_at = _now_iso()
    db.execute(
        """
        INSERT INTO student_accessibility_preferences (
            student_id, session_id, mode, translation_language,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, session_id) DO NOTHING
        """,
        (
            student_id,
            session_id,
            DEFAULT_MODE,
            DEFAULT_TRANSLATION_LANGUAGE,
            created_at,
            created_at,
        ),
    )
    db.commit()
    return find_preference(db, student_id=student_id, session_id=session_id)


def save_preference(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
    mode: str,
    translation_language: str,
) -> dict:
    """Upsert only the requesting Student's row for this lecture."""
    timestamp = _now_iso()
    db.execute(
        """
        INSERT INTO student_accessibility_preferences (
            student_id, session_id, mode, translation_language,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, session_id) DO UPDATE SET
            mode = excluded.mode,
            translation_language = excluded.translation_language,
            updated_at = excluded.updated_at
        """,
        (
            student_id,
            session_id,
            mode,
            translation_language,
            timestamp,
            timestamp,
        ),
    )
    db.commit()
    return find_preference(db, student_id=student_id, session_id=session_id)
