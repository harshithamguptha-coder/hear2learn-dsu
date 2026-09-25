"""Pydantic request and response models for the public API."""

from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["en", "kn", "hi", "te"]
AccessibilityMode = Literal["standard", "simplified", "translation", "sign_support"]
TranslationLanguage = Literal["kn", "hi", "te"]


UserRole = Literal["teacher", "student"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class LectureCreate(BaseModel):
    title: str = Field(default="Untitled Lecture", min_length=1, max_length=200)


class SessionResponse(BaseModel):
    session_id: str
    status: Literal["active", "ended"]
    started_at: str
    ended_at: str | None = None
    teacher_id: int | None = None
    title: str = "Untitled Lecture"
    start_time: str | None = None
    end_time: str | None = None


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


class TopicSegment(BaseModel):
    topic: str
    timestamp: str | None = None


class DefinitionItem(BaseModel):
    term: str
    definition: str


class ExampleItem(BaseModel):
    concept: str
    example: str


class ImportantMomentItem(BaseModel):
    type: str
    content: str
    timestamp: str | None = None


class StructuredTranscriptResponse(BaseModel):
    clean_text: str
    topic: str
    key_points: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    technical_terms: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    speaker_segments: list[SpeakerSegment] = Field(default_factory=list)
    topic_history: list[TopicSegment] = Field(default_factory=list)
    important_points: list[str] = Field(default_factory=list)
    definitions: list[DefinitionItem] = Field(default_factory=list)
    examples: list[ExampleItem] = Field(default_factory=list)
    important_moments: list[ImportantMomentItem] = Field(default_factory=list)


class LectureQARequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)
    conversation_id: str | None = None


class LectureQAResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    lecture_grounded: bool
    conversation_id: str


class ConversationMessageResponse(BaseModel):
    id: int
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[str] = Field(default_factory=list)
    lecture_grounded: bool
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: str
    session_id: str
    messages: list[ConversationMessageResponse] = Field(default_factory=list)
    created_at: str


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)
    target_language: LanguageCode


class TranslationResponse(BaseModel):
    session_id: str
    source_language: Literal["en"]
    target_language: LanguageCode
    original_text: str
    translated_text: str


class AccessibilityPreferenceUpdate(BaseModel):
    mode: AccessibilityMode
    translation_language: TranslationLanguage = "kn"


class AccessibilityPreferenceResponse(BaseModel):
    student_id: int
    session_id: str
    mode: AccessibilityMode
    translation_language: TranslationLanguage
    created_at: str
    updated_at: str


class AccessibilityUsage(BaseModel):
    standard: int = Field(default=0, ge=0)
    simplified: int = Field(default=0, ge=0)
    translation: int = Field(default=0, ge=0)
    sign_support: int = Field(default=0, ge=0)


class TeacherLectureAnalytics(BaseModel):
    session_id: str
    title: str
    lecture_date: str
    start_time: str
    end_time: str | None = None
    duration_seconds: int = Field(default=0, ge=0)
    students_attended: int = Field(default=0, ge=0)
    questions_asked: int = Field(default=0, ge=0)
    detected_topics: list[str] = Field(default_factory=list)
    accessibility_usage: AccessibilityUsage
    status: Literal["active", "ended"]


class TeacherDashboardResponse(BaseModel):
    teacher_id: int
    total_lectures: int = Field(default=0, ge=0)
    lectures: list[TeacherLectureAnalytics] = Field(default_factory=list)


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


AttendanceStatus = Literal["in_progress", "attended"]


class LectureAttendanceResponse(BaseModel):
    id: int
    student_id: int
    session_id: str
    joined_at: str
    left_at: str | None = None


class MyLectureResponse(BaseModel):
    session_id: str
    title: str
    teacher: str
    lecture_date: str
    joined_at: str
    left_at: str | None = None
    duration_seconds: int
    status: AttendanceStatus
