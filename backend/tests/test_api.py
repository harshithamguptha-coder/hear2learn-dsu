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
