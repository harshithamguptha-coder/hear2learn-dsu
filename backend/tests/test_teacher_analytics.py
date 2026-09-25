"""Teacher dashboard analytics from real persisted application records."""

from app.services.ai_structuring import HeuristicAIProvider, ai_structuring_service


PASSWORD = "teacher-analytics-password-123"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, email, role):
    response = client.post(
        "/api/auth/register",
        json={"name": f"Analytics {role.title()}", "email": email, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201
    return response.json()


def create_lecture(client, teacher, title):
    response = client.post(
        "/api/lectures", headers=auth_header(teacher["access_token"]), json={"title": title}
    )
    assert response.status_code == 201
    return response.json()


def join_lecture(client, session_id, student):
    response = client.post(
        f"/api/sessions/{session_id}/attendance/join",
        headers=auth_header(student["access_token"]),
    )
    assert response.status_code == 201


def set_mode(client, session_id, student, mode):
    response = client.post(
        f"/api/sessions/{session_id}/accessibility",
        headers=auth_header(student["access_token"]),
        json={"mode": mode, "translation_language": "kn"},
    )
    assert response.status_code == 200


def test_completed_lecture_analytics_use_real_teacher_scoped_records(client, monkeypatch):
    from app import database

    monkeypatch.setattr(ai_structuring_service, "_provider", HeuristicAIProvider())
    teacher = register(client, "analytics-teacher@example.com", "teacher")
    other_teacher = register(client, "analytics-other-teacher@example.com", "teacher")
    first_student = register(client, "analytics-first@example.com", "student")
    second_student = register(client, "analytics-second@example.com", "student")
    lecture = create_lecture(client, teacher, "Python Functions")
    session_id = lecture["session_id"]

    join_lecture(client, session_id, first_student)
    join_lecture(client, session_id, second_student)
    set_mode(client, session_id, first_student, "simplified")
    set_mode(client, session_id, second_student, "sign_support")

    transcript = (
        "Today we explore Python functions and parameters. "
        "A function receives input values and returns a result to the caller. "
        "Clear function names make programs easier to understand and test."
    )
    assert client.post(
        f"/api/sessions/{session_id}/transcript", json={"text": transcript}
    ).status_code == 201
    for question in (
        "What does a Python function receive?",
        "Why are clear function names useful?",
    ):
        assert client.post(
            f"/api/sessions/{session_id}/qa", json={"question": question}
        ).status_code == 200

    assert client.post(f"/api/sessions/{session_id}/end").status_code == 200
    stored_notes = client.get(f"/api/sessions/{session_id}/notes").json()
    connection = database.connect_db()
    try:
        connection.execute(
            "UPDATE sessions SET start_time = ?, end_time = ? WHERE session_id = ?",
            ("2026-01-15T10:00:00+00:00", "2026-01-15T11:30:00+00:00", session_id),
        )
        connection.commit()
    finally:
        connection.close()

    response = client.get("/api/teacher/dashboard", headers=auth_header(teacher["access_token"]))
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["teacher_id"] == teacher["user"]["id"]
    assert dashboard["total_lectures"] == 1
    analytics = dashboard["lectures"][0]
    assert analytics["session_id"] == session_id
    assert analytics["title"] == "Python Functions"
    assert analytics["lecture_date"] == "2026-01-15T10:00:00+00:00"
    assert analytics["start_time"] == "2026-01-15T10:00:00+00:00"
    assert analytics["end_time"] == "2026-01-15T11:30:00+00:00"
    assert analytics["duration_seconds"] == 5400
    assert analytics["students_attended"] == 2
    assert analytics["questions_asked"] == 2
    assert analytics["detected_topics"] == stored_notes["main_topics"]
    assert analytics["detected_topics"]
    assert analytics["accessibility_usage"] == {
        "standard": 0, "simplified": 1, "translation": 0, "sign_support": 1,
    }

    other_lecture = create_lecture(client, other_teacher, "Other Teacher Lecture")
    other_dashboard = client.get(
        "/api/teacher/dashboard", headers=auth_header(other_teacher["access_token"])
    ).json()
    assert [item["session_id"] for item in other_dashboard["lectures"]] == [
        other_lecture["session_id"]
    ]
    other_item = other_dashboard["lectures"][0]
    assert other_item["end_time"] is None
    assert other_item["duration_seconds"] == 0
    assert other_item["students_attended"] == 0
    assert other_item["questions_asked"] == 0
    assert other_item["detected_topics"] == []
    assert other_item["accessibility_usage"] == {
        "standard": 0, "simplified": 0, "translation": 0, "sign_support": 0,
    }
    assert client.get("/api/teacher/dashboard").status_code == 401
    assert client.get(
        "/api/teacher/dashboard", headers=auth_header(first_student["access_token"])
    ).status_code == 403
