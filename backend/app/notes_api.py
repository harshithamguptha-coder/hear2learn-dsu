"""Read the generated notes for one lecture session."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from .database import get_db
from .models import LectureNotesResponse
from .services import session_service
from .services.notes_service import NotesService

router = APIRouter(tags=["lecture notes"])


def get_notes_service(request: Request) -> NotesService:
    return request.app.state.notes_service


@router.get(
    "/sessions/{session_id}/notes",
    response_model=LectureNotesResponse,
)
def get_lecture_notes(
    session_id: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    notes_service: NotesService = Depends(get_notes_service),
) -> dict:
    session = session_service.find_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    if session["status"] != "ended":
        raise HTTPException(
            status_code=409,
            detail="Lecture notes are available after the lecture ends.",
        )

    notes = notes_service.find_by_session(db, session_id)
    if notes is None:
        raise HTTPException(
            status_code=404,
            detail="Lecture notes were not generated for this session.",
        )
    return notes
