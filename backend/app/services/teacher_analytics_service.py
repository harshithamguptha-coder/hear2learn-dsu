"""Teacher-only lecture analytics aggregated from persisted classroom records."""

import json
import sqlite3
from datetime import datetime, timezone


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _duration_seconds(start_time: str | None, end_time: str | None) -> int:
    start = _parse_time(start_time)
    end = _parse_time(end_time)
    if start is None or end is None:
        return 0
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds()))


def _stored_topics(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        topics = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(topics, list):
        return []
    return [topic.strip() for topic in topics if isinstance(topic, str) and topic.strip()]


def get_teacher_dashboard(db: sqlite3.Connection, *, teacher_id: int) -> dict:
    """Return only sessions owned by ``teacher_id`` and their real aggregates."""
    rows = db.execute(
        """
        SELECT
            session.session_id,
            COALESCE(session.title, 'Untitled Lecture') AS title,
            COALESCE(session.start_time, session.started_at) AS lecture_date,
            COALESCE(session.start_time, session.started_at) AS start_time,
            COALESCE(session.end_time, session.ended_at) AS end_time,
            session.status,
            (
                SELECT COUNT(DISTINCT attendance.student_id)
                FROM lecture_attendance AS attendance
                WHERE attendance.session_id = session.session_id
            ) AS students_attended,
            (
                SELECT COUNT(*)
                FROM conversation_messages AS message
                JOIN conversations AS conversation
                    ON conversation.id = message.conversation_id
                WHERE conversation.session_id = session.session_id
                  AND message.role = 'user'
                  AND TRIM(message.content) <> ''
            ) AS questions_asked,
            (
                SELECT COUNT(*) FROM student_accessibility_preferences AS preference
                WHERE preference.session_id = session.session_id
                  AND preference.mode = 'standard'
            ) AS usage_standard,
            (
                SELECT COUNT(*) FROM student_accessibility_preferences AS preference
                WHERE preference.session_id = session.session_id
                  AND preference.mode = 'simplified'
            ) AS usage_simplified,
            (
                SELECT COUNT(*) FROM student_accessibility_preferences AS preference
                WHERE preference.session_id = session.session_id
                  AND preference.mode = 'translation'
            ) AS usage_translation,
            (
                SELECT COUNT(*) FROM student_accessibility_preferences AS preference
                WHERE preference.session_id = session.session_id
                  AND preference.mode = 'sign_support'
            ) AS usage_sign_support,
            notes.main_topics
        FROM sessions AS session
        LEFT JOIN lecture_notes AS notes
            ON notes.session_id = session.session_id
        WHERE session.teacher_id = ?
        ORDER BY COALESCE(session.start_time, session.started_at) DESC,
                 session.session_id DESC
        """,
        (teacher_id,),
    ).fetchall()

    lectures = []
    for row in rows:
        item = dict(row)
        lectures.append({
            "session_id": item["session_id"],
            "title": item["title"],
            "lecture_date": item["lecture_date"],
            "start_time": item["start_time"],
            "end_time": item["end_time"],
            "duration_seconds": _duration_seconds(item["start_time"], item["end_time"]),
            "students_attended": item["students_attended"],
            "questions_asked": item["questions_asked"],
            "detected_topics": _stored_topics(item["main_topics"]),
            "accessibility_usage": {
                "standard": item["usage_standard"],
                "simplified": item["usage_simplified"],
                "translation": item["usage_translation"],
                "sign_support": item["usage_sign_support"],
            },
            "status": item["status"],
        })

    return {
        "teacher_id": teacher_id,
        "total_lectures": len(lectures),
        "lectures": lectures,
    }
