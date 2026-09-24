"""Authenticated Student attendance and personal lecture-history routes."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .auth_api import require_student
from .database import get_db
from .models import LectureAttendanceResponse, MyLectureResponse
from .services import attendance_service, session_service

router = APIRouter(tags=["student attendance"])


@router.post(
    "/sessions/{session_id}/attendance/join",
    response_model=LectureAttendanceResponse,
    status_code=201,
)
def join_lecture(
    session_id: str,
    student: dict = Depends(require_student),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    session = session_service.find_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    if session["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail="Attendance can only be recorded while the lecture is active.",
        )

    attendance = attendance_service.join_lecture(
        db,
        student_id=student["id"],
        session_id=session_id,
    )
    return attendance


@router.post(
    "/sessions/{session_id}/attendance/leave",
    response_model=LectureAttendanceResponse,
)
def leave_lecture(
    session_id: str,
    student: dict = Depends(require_student),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    attendance = attendance_service.leave_lecture(
        db,
        student_id=student["id"],
        session_id=session_id,
    )
    if attendance is None:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    return attendance


@router.get("/my-lectures", response_model=list[MyLectureResponse])
def my_lectures(
    student: dict = Depends(require_student),
    db: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return attendance_service.list_student_lectures(db, student_id=student["id"])
