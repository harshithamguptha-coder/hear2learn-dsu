"""HTTP endpoints for lectures and their transcripts."""

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .database import get_db
from .models import SessionResponse, TranscriptCreate, TranscriptResponse
from .services import session_service
from .services.realtime import EventHub

router = APIRouter(tags=["lectures"])


def get_event_hub(request: Request) -> EventHub:
    return request.app.state.event_hub


def get_notes_service(request: Request):
    return request.app.state.notes_service


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=201,
)
def create_session(db: sqlite3.Connection = Depends(get_db)) -> dict:
    return session_service.create_session(db)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    session = session_service.find_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    return session


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    db: sqlite3.Connection = Depends(get_db),
    event_hub: EventHub = Depends(get_event_hub),
    notes_service=Depends(get_notes_service),
) -> dict:
    current = session_service.find_session(db, session_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")

    if current["status"] == "active":
        transcript = session_service.list_transcript(db, session_id)
        notes_service.generate_and_save(db, session_id, transcript)
        session = session_service.end_session(db, session_id)
        await event_hub.publish(
            session_id,
            {"event": "session_ended", "session_id": session_id},
        )
        return session

    return session_service.end_session(db, session_id)


@router.get(
    "/sessions/{session_id}/transcript",
    response_model=list[TranscriptResponse],
)
def get_transcript(
    session_id: str,
    db: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    if session_service.find_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    return session_service.list_transcript(db, session_id)


@router.post(
    "/sessions/{session_id}/transcript",
    response_model=TranscriptResponse,
    status_code=201,
)
async def save_transcript(
    session_id: str,
    payload: TranscriptCreate,
    db: sqlite3.Connection = Depends(get_db),
    event_hub: EventHub = Depends(get_event_hub),
) -> dict:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Transcript text cannot be empty.")

    transcript = session_service.add_transcript(db, session_id, text)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")
    if transcript.get("error"):
        raise HTTPException(status_code=400, detail=transcript["error"])

    await event_hub.publish(session_id, transcript)
    return transcript


def encode_event(event_name: str, data: object) -> str:
    """Encode one named Server-Sent Event."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


@router.get("/sessions/{session_id}/events")
async def stream_session_events(
    session_id: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    event_hub: EventHub = Depends(get_event_hub),
) -> StreamingResponse:
    """Send saved text first, then live text as the teacher speaks."""
    if session_service.find_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Lecture session not found.")

    async def event_stream() -> AsyncIterator[str]:
        queue = event_hub.subscribe(session_id)
        try:
            yield "retry: 3000\n\n"
            saved_items = session_service.list_transcript(db, session_id)
            yield encode_event("snapshot", saved_items)
            seen_ids = {item["id"] for item in saved_items}

            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                if item.get("event") == "session_ended":
                    yield encode_event("session-ended", item)
                    continue

                # A request between subscribing and the snapshot can otherwise
                # appear in both responses. Transcript IDs make that harmless.
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    yield encode_event("transcript", item)
        finally:
            event_hub.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
