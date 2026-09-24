"""Pydantic request and response models for the public API."""

from typing import Literal

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    session_id: str
    status: Literal["active", "ended"]
    started_at: str
    ended_at: str | None = None


class TranscriptCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)


class TranscriptResponse(BaseModel):
    id: int
    session_id: str
    text: str
    created_at: str
