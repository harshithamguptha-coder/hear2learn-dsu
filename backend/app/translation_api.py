"""Session-scoped translation endpoints kept separate from lecture APIs."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from .database import get_db
from .models import TranslationRequest, TranslationResponse
from .services import session_service
from .services.translation_service import TranslationService, TranslationServiceError

router = APIRouter(tags=["translation"])


def get_translation_service(request: Request) -> TranslationService:
    return request.app.state.translation_service


@router.post(
    "/sessions/{session_id}/translations",
    response_model=TranslationResponse,
)
async def translate_transcript_segment(
    session_id: str,
    payload: TranslationRequest,
    db: sqlite3.Connection = Depends(get_db),
    translation_service: TranslationService = Depends(get_translation_service),
) -> dict:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Text to translate cannot be empty.")
    if session_service.find_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")

    try:
        translated_text = await translation_service.translate(
            text,
            payload.target_language,
        )
    except TranslationServiceError as error:
        raise HTTPException(
            status_code=503,
            detail="Translation is temporarily unavailable. The original transcript is unchanged.",
        ) from error

    return {
        "session_id": session_id,
        "source_language": "en",
        "target_language": payload.target_language,
        "original_text": text,
        "translated_text": translated_text,
    }
