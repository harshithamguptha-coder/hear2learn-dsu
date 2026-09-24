"""Pydantic request and response models for the public API."""

from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["en", "kn", "hi", "te"]


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


SpeakerRole = Literal["Teacher", "Student", "Unknown"]


class SpeakerSegment(BaseModel):
    speaker: SpeakerRole
    text: str
    timestamp: str | None = None


class TranscriptStructureRequest(BaseModel):
    text: str | None = Field(default=None, max_length=50_000)


class StructuredTranscriptResponse(BaseModel):
    clean_text: str
    topic: str
    key_points: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    technical_terms: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    speaker_segments: list[SpeakerSegment] = Field(default_factory=list)


class LectureQARequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)


class LectureQAResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    lecture_grounded: bool


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)
    target_language: LanguageCode


class TranslationResponse(BaseModel):
    session_id: str
    source_language: Literal["en"]
    target_language: LanguageCode
    original_text: str
    translated_text: str


class LectureNotesResponse(BaseModel):
    session_id: str
    status: Literal["ready", "too_short"]
    title: str
    summary: str
    main_topics: list[str]
    key_points: list[str]
    important_terms: list[str]
    message: str | None = None
    created_at: str
