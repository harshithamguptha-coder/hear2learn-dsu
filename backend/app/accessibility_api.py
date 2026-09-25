"""Authenticated Student routes for per-lecture accessibility preferences."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .auth_api import require_student
from .database import get_db
from .models import AccessibilityPreferenceResponse, AccessibilityPreferenceUpdate
from .services import accessibility_service, attendance_service, session_service

router = APIRouter(tags=["student accessibility"])


def _require_joined_session(
    db: sqlite3.Connection,
    *,
    session_id: str,
    student_id: int,
) -> None:
    if session_service.find_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    if attendance_service.find_attendance(
        db,
        student_id=student_id,
        session_id=session_id,
    ) is None:
        raise HTTPException(
            status_code=403,
            detail="Join this lecture before choosing an accessibility mode.",
        )


@router.get(
    "/sessions/{session_id}/accessibility",
    response_model=AccessibilityPreferenceResponse,
)
def get_accessibility_preference(
    session_id: str,
    student: dict = Depends(require_student),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Return only the logged-in Student's preference for this session."""
    _require_joined_session(
        db,
        session_id=session_id,
        student_id=student["id"],
    )
    return accessibility_service.get_or_create_preference(
        db,
        student_id=student["id"],
        session_id=session_id,
    )


@router.post(
    "/sessions/{session_id}/accessibility",
    response_model=AccessibilityPreferenceResponse,
)
def save_accessibility_preference(
    session_id: str,
    payload: AccessibilityPreferenceUpdate,
    student: dict = Depends(require_student),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Save the logged-in Student's mode without changing any other Student."""
    _require_joined_session(
        db,
        session_id=session_id,
        student_id=student["id"],
    )
    return accessibility_service.save_preference(
        db,
        student_id=student["id"],
        session_id=session_id,
        mode=payload.mode,
        translation_language=payload.translation_language,
    )
