"""Focused tests for deterministic lecture note generation."""

from app.services.notes_service import generate_content, split_sentences


def test_generate_content_returns_all_study_note_sections():
    sentences = [
        "Today we explore Python functions and their parameters.",
        "A function accepts input values and returns a useful result.",
        "Testing each function with clear examples catches mistakes early.",
    ]
    notes = generate_content(sentences)

    assert notes["status"] == "ready"
    assert notes["title"]
    assert notes["summary"]
    assert "Python" in notes["main_topics"]
    assert notes["key_points"]
    assert "Python" in notes["important_terms"]
    assert notes["message"] is None


def test_short_transcript_returns_useful_message():
    notes = generate_content(["Good morning."])

    assert notes["status"] == "too_short"
    assert notes["message"]
    assert notes["key_points"] == []
    assert notes["main_topics"] == []


def test_split_sentences_keeps_transcript_segments_in_order():
    transcript = [
        {"text": "First idea. Second idea."},
        {"text": "Third idea."},
    ]
    assert split_sentences(transcript) == [
        "First idea.",
        "Second idea.",
        "Third idea.",
    ]
