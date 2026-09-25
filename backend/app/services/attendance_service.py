"""Persistent attendance recording and Student-only lecture history."""

import sqlite3
from datetime import datetime, timezone

from .accessibility_service import DEFAULT_MODE, DEFAULT_TRANSLATION_LANGUAGE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _duration_seconds(joined_at: str, left_at: str | None) -> int:
    start = _parse_time(joined_at)
    end = _parse_time(left_at) if left_at else datetime.now(timezone.utc)
    if start is None or end is None:
        return 0
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds()))


def join_lecture(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
) -> dict | None:
    """Create attendance, or reopen the same Student's existing row."""
    joined_at = _now_iso()
    db.execute(
        """
        INSERT INTO lecture_attendance (student_id, session_id, joined_at)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id, session_id) DO UPDATE SET
            joined_at = CASE
                WHEN lecture_attendance.left_at IS NULL
                    THEN lecture_attendance.joined_at
                ELSE excluded.joined_at
            END,
            left_at = NULL
        """,
        (student_id, session_id, joined_at),
    )
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
            joined_at,
            joined_at,
        ),
    )
    db.commit()
    return find_attendance(db, student_id=student_id, session_id=session_id)


def find_attendance(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
) -> dict | None:
    row = db.execute(
        """
        SELECT id, student_id, session_id, joined_at, left_at
        FROM lecture_attendance
        WHERE student_id = ? AND session_id = ?
        """,
        (student_id, session_id),
    ).fetchone()
    return dict(row) if row else None


def leave_lecture(
    db: sqlite3.Connection,
    *,
    student_id: int,
    session_id: str,
) -> dict | None:
    left_at = _now_iso()
    db.execute(
        """
        UPDATE lecture_attendance
        SET left_at = COALESCE(left_at, ?)
        WHERE student_id = ? AND session_id = ?
        """,
        (left_at, student_id, session_id),
    )
    db.commit()
    return find_attendance(db, student_id=student_id, session_id=session_id)


def close_lecture_attendance(
    db: sqlite3.Connection,
    *,
    session_id: str,
    left_at: str,
) -> None:
    """Close all open attendance rows when the Teacher ends the lecture."""
    db.execute(
        """
        UPDATE lecture_attendance
        SET left_at = COALESCE(left_at, ?)
        WHERE session_id = ? AND left_at IS NULL
        """,
        (left_at, session_id),
    )
    db.commit()


def list_student_lectures(
    db: sqlite3.Connection,
    *,
    student_id: int,
) -> list[dict]:
    rows = db.execute(
        """
        SELECT
            attendance.session_id,
            attendance.joined_at,
            attendance.left_at,
            COALESCE(session.title, 'Untitled Lecture') AS title,
            COALESCE(session.start_time, session.started_at) AS lecture_date,
            COALESCE(session.end_time, session.ended_at) AS lecture_end,
            session.status AS session_status,
            teacher.name AS teacher
        FROM lecture_attendance AS attendance
        JOIN sessions AS session ON session.session_id = attendance.session_id
        LEFT JOIN users AS teacher ON teacher.id = session.teacher_id
        WHERE attendance.student_id = ?
        ORDER BY attendance.joined_at DESC
        """,
        (student_id,),
    ).fetchall()

    lectures = []
    for row in rows:
        item = dict(row)
        effective_end = item["left_at"] or item["lecture_end"]
        lectures.append({
            "session_id": item["session_id"],
            "title": item["title"],
            "teacher": item["teacher"] or "Unknown Teacher",
            "lecture_date": item["lecture_date"],
            "joined_at": item["joined_at"],
            "left_at": item["left_at"],
            "duration_seconds": _duration_seconds(
                item["joined_at"],
                effective_end,
            ),
            "status": (
                "in_progress"
                if item["left_at"] is None and item["session_status"] == "active"
                else "attended"
            ),
        })
    return lectures
