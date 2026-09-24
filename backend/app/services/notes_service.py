"""Deterministic, session-scoped lecture note generation.

The project has no LLM configuration, so this MVP uses a small extractive
summarizer built entirely with Python's standard library. A future LLM-backed
generator can replace NotesService without changing the API or database.
"""

import json
import re
import sqlite3
from collections import Counter

from .session_service import now_iso

MIN_TRANSCRIPT_WORDS = 20
MAX_KEY_POINTS = 5

STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "before",
    "being", "between", "both", "but", "can", "could", "does", "each", "from",
    "have", "having", "here", "how", "into", "its", "just", "more", "most", "not",
    "now", "only", "other", "our", "over", "please", "same", "should", "some",
    "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "today", "very", "was", "were", "what",
    "when", "where", "which", "while", "who", "why", "will", "with", "would",
    "your", "you", "lecture", "class", "learn", "learning", "learned",
    "good", "morning", "explore", "clear", "short", "examples", "example",
    "make", "makes", "easier", "understand", "receive", "receives", "returns",
    "names", "code", "values", "value", "caller",
}


def words_in(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.lower())


def split_sentences(transcript: list[dict]) -> list[str]:
    sentences = []
    for item in transcript:
        parts = re.split(r"(?<=[.!?])\s+|\n+", item["text"].strip())
        sentences.extend(part.strip() for part in parts if part.strip())
    return sentences


def display_term(term: str) -> str:
    return term[:1].upper() + term[1:]


def make_title(sentences: list[str]) -> str:
    greeting_only = {"good morning", "hello", "welcome", "any questions", "thank you"}
    for sentence in sentences:
        normalized = re.sub(r"[^a-z ]", "", sentence.lower()).strip()
        if normalized not in greeting_only:
            title = sentence.rstrip(".!?").strip()
            title = re.sub(
                r"^(today|in this lecture)\s+we\s+(will\s+)?"
                r"(explore|discuss|learn about|cover)\s+",
                "",
                title,
                flags=re.IGNORECASE,
            )
            if title:
                title = title[:1].upper() + title[1:]
            if len(title) > 90:
                title = title[:87].rstrip() + "…"
            return title
    return (sentences[0].rstrip(".!?").strip() if sentences else "Lecture Notes")[:90]


def generate_content(sentences: list[str]) -> dict:
    all_words = words_in(" ".join(sentences))
    if len(all_words) < MIN_TRANSCRIPT_WORDS:
        return {
            "status": "too_short",
            "title": "Lecture Notes Not Available",
            "summary": (
                "This lecture ended with too little spoken content to create "
                "useful notes."
            ),
            "main_topics": [],
            "key_points": [],
            "important_terms": [],
            "message": (
                "The transcript is too short. A longer lecture transcript is "
                "needed to generate a summary and study notes."
            ),
        }

    frequencies = Counter(
        word for word in all_words if len(word) >= 4 and word not in STOP_WORDS
    )
    ranked_terms = [
        word for word, _ in sorted(
            frequencies.items(),
            key=lambda item: (-item[1], all_words.index(item[0])),
        )
    ]
    main_topics = [display_term(word) for word in ranked_terms[:5]]
    important_terms = [display_term(word) for word in ranked_terms[:8]]

    first_seen = set()
    unique_sentences = []
    for sentence in sentences:
        normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
        if normalized and normalized not in first_seen:
            first_seen.add(normalized)
            unique_sentences.append(sentence)

    def sentence_score(index: int, sentence: str) -> float:
        sentence_words = [word for word in words_in(sentence) if word in frequencies]
        return (len(set(sentence_words)) * 2) + (1 / (index + 1))

    ranked_sentences = sorted(
        enumerate(unique_sentences),
        key=lambda item: sentence_score(item[0], item[1]),
        reverse=True,
    )
    key_points = [sentence for _, sentence in ranked_sentences[:MAX_KEY_POINTS]]
    key_points.sort(key=lambda sentence: unique_sentences.index(sentence))

    if main_topics:
        topic_text = ", ".join(topic.lower() for topic in main_topics[:3])
        summary = f"This lecture focuses on {topic_text}."
    else:
        summary = "This lecture introduces the main ideas shared during the session."

    summary_points = " ".join(key_points[:2])
    if len(summary_points) > 360:
        summary_points = summary_points[:357].rstrip() + "…"
    summary = f"{summary} {summary_points}".strip()

    return {
        "status": "ready",
        "title": make_title(sentences),
        "summary": summary,
        "main_topics": main_topics,
        "key_points": key_points,
        "important_terms": important_terms,
        "message": None,
    }


class NotesService:
    def generate_and_save(
        self,
        db: sqlite3.Connection,
        session_id: str,
        transcript: list[dict],
    ) -> dict:
        existing = self.find_by_session(db, session_id)
        if existing:
            return existing

        content = generate_content(split_sentences(transcript))
        created_at = now_iso()
        db.execute(
            """
            INSERT INTO lecture_notes (
                session_id, status, title, summary, main_topics, key_points,
                important_terms, message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                content["status"],
                content["title"],
                content["summary"],
                json.dumps(content["main_topics"], ensure_ascii=False),
                json.dumps(content["key_points"], ensure_ascii=False),
                json.dumps(content["important_terms"], ensure_ascii=False),
                content["message"],
                created_at,
            ),
        )
        db.commit()
        return self.find_by_session(db, session_id)

    def find_by_session(
        self,
        db: sqlite3.Connection,
        session_id: str,
    ) -> dict | None:
        row = db.execute(
            """
            SELECT session_id, status, title, summary, main_topics, key_points,
                   important_terms, message, created_at
            FROM lecture_notes
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        notes = dict(row)
        for field in ("main_topics", "key_points", "important_terms"):
            notes[field] = json.loads(notes[field])
        return notes
