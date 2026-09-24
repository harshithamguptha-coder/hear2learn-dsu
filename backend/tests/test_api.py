"""Foundation API tests, including SQLite persistence and live event delivery."""

import asyncio

from app.services.realtime import EventHub


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_end_session(client):
    first = client.post("/api/sessions")
    second = client.post("/api/sessions")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["session_id"] != second.json()["session_id"]
    assert first.json()["status"] == "active"

    session_id = first.json()["session_id"]
    ended = client.post(f"/api/sessions/{session_id}/end")
    ended_again = client.post(f"/api/sessions/{session_id}/end")

    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"
    assert ended_again.status_code == 200
    assert ended_again.json()["ended_at"] == ended.json()["ended_at"]


def test_unknown_session_returns_404(client):
    response = client.get("/api/sessions/NOT-A-SESSION")
    assert response.status_code == 404


def test_transcript_is_saved_against_session(client):
    session_id = client.post("/api/sessions").json()["session_id"]
    saved = client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Welcome to today's lecture."},
    )

    assert saved.status_code == 201
    assert saved.json()["session_id"] == session_id

    transcript = client.get(f"/api/sessions/{session_id}/transcript")
    assert transcript.status_code == 200
    assert [item["text"] for item in transcript.json()] == [
        "Welcome to today's lecture."
    ]


def test_blank_or_ended_transcript_is_rejected(client):
    session_id = client.post("/api/sessions").json()["session_id"]
    blank = client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "   "},
    )
    assert blank.status_code == 422

    client.post(f"/api/sessions/{session_id}/end")
    ended = client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Too late"},
    )
    assert ended.status_code == 400


def test_translation_endpoint_uses_session_and_keeps_original(client, monkeypatch):
    session_id = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Welcome to today's lecture."},
    )

    async def fake_translate(text, target_language):
        return {
            "kn": "ಇಂದಿನ ಉಪನ್ಯಾಸಕ್ಕೆ ಸುಸ್ವಾಗತ.",
            "hi": "आज के व्याख्यान में आपका स्वागत है।",
            "te": "హాయ్ ఆండీ",
        }[target_language]

    monkeypatch.setattr(client.app.state.translation_service, "translate", fake_translate)
    response = client.post(
        f"/api/sessions/{session_id}/translations",
        json={"text": "Welcome to today's lecture.", "target_language": "kn"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session_id,
        "source_language": "en",
        "target_language": "kn",
        "original_text": "Welcome to today's lecture.",
        "translated_text": "ಇಂದಿನ ಉಪನ್ಯಾಸಕ್ಕೆ ಸುಸ್ವಾಗತ.",
    }
    original = client.get(f"/api/sessions/{session_id}/transcript").json()
    assert [item["text"] for item in original] == ["Welcome to today's lecture."]

    telugu = client.post(
        f"/api/sessions/{session_id}/translations",
        json={"text": "Good morning", "target_language": "te"},
    )
    assert telugu.status_code == 200
    assert telugu.json()["translated_text"] == "హాయ్ ఆండీ"


def test_translation_rejects_unknown_session_and_language(client):
    unknown = client.post(
        "/api/sessions/NOT-A-SESSION/translations",
        json={"text": "Hello", "target_language": "hi"},
    )
    assert unknown.status_code == 404

    session_id = client.post("/api/sessions").json()["session_id"]
    unsupported = client.post(
        f"/api/sessions/{session_id}/translations",
        json={"text": "Hello", "target_language": "fr"},
    )
    assert unsupported.status_code == 422


def test_end_session_generates_session_scoped_notes(client):
    first_id = client.post("/api/sessions").json()["session_id"]
    second_id = client.post("/api/sessions").json()["session_id"]
    first_lines = [
        "Good morning. Today we explore Python functions and parameters.",
        "A function receives input values and returns a result to the caller.",
        "Clear names and short examples make code easier to understand and test.",
    ]
    second_lines = [
        "This session studies the water cycle in our geography lesson.",
        "Evaporation moves water into the atmosphere before condensation begins.",
        "Clouds form when water vapor cools and becomes tiny liquid droplets.",
    ]
    for text in first_lines:
        assert client.post(
            f"/api/sessions/{first_id}/transcript", json={"text": text}
        ).status_code == 201
    for text in second_lines:
        assert client.post(
            f"/api/sessions/{second_id}/transcript", json={"text": text}
        ).status_code == 201

    before_end = client.get(f"/api/sessions/{first_id}/notes")
    assert before_end.status_code == 409

    assert client.post(f"/api/sessions/{first_id}/end").status_code == 200
    assert client.post(f"/api/sessions/{second_id}/end").status_code == 200

    first_notes = client.get(f"/api/sessions/{first_id}/notes")
    second_notes = client.get(f"/api/sessions/{second_id}/notes")
    assert first_notes.status_code == 200
    assert second_notes.status_code == 200
    assert first_notes.json()["status"] == "ready"
    assert second_notes.json()["status"] == "ready"
    assert first_notes.json()["session_id"] == first_id
    assert second_notes.json()["session_id"] == second_id
    assert "Python" in first_notes.json()["summary"]
    assert "water" in second_notes.json()["summary"].lower()
    assert "Python" not in second_notes.json()["summary"]
    assert "water" not in first_notes.json()["summary"].lower()
    assert first_notes.json()["key_points"]
    assert first_notes.json()["important_terms"]


def test_too_short_transcript_returns_useful_notes(client):
    session_id = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Good morning."},
    )
    client.post(f"/api/sessions/{session_id}/end")

    response = client.get(f"/api/sessions/{session_id}/notes")
    assert response.status_code == 200
    assert response.json()["status"] == "too_short"
    assert response.json()["message"]
    assert response.json()["key_points"] == []
    assert client.get(f"/api/sessions/{session_id}/transcript").json()[0]["text"] == "Good morning."


def test_notes_reject_unknown_session(client):
    response = client.get("/api/sessions/UNKNOWN/notes")
    assert response.status_code == 404


def test_event_hub_delivers_transcript_to_session_subscriber():
    async def check_delivery():
        hub = EventHub()
        first_queue = hub.subscribe("lecture-one")
        second_queue = hub.subscribe("lecture-two")
        message = {"id": 1, "session_id": "lecture-one", "text": "Hello"}

        await hub.publish("lecture-one", message)

        assert await first_queue.get() == message
        assert second_queue.empty()

    asyncio.run(check_delivery())
