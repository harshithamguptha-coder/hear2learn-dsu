"""Tests for private, durable Student accessibility preferences."""

from app import database


PASSWORD = "accessibility-password-123"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, email, role):
    response = client.post(
        "/api/auth/register",
        json={
            "name": f"Accessibility {role.title()}",
            "email": email,
            "password": PASSWORD,
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_lecture(client, teacher):
    response = client.post(
        "/api/lectures",
        headers=auth_header(teacher["access_token"]),
        json={"title": "Accessibility Lecture"},
    )
    assert response.status_code == 201
    return response.json()


def join_lecture(client, session_id, student):
    response = client.post(
        f"/api/sessions/{session_id}/attendance/join",
        headers=auth_header(student["access_token"]),
    )
    assert response.status_code == 201


def login(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def get_preference(client, session_id, token):
    response = client.get(
        f"/api/sessions/{session_id}/accessibility",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    return response.json()


def save_preference(client, session_id, token, mode, language="kn"):
    response = client.post(
        f"/api/sessions/{session_id}/accessibility",
        headers=auth_header(token),
        json={"mode": mode, "translation_language": language},
    )
    assert response.status_code == 200
    return response.json()


def test_two_students_in_one_lecture_keep_independent_modes(client):
    teacher = register(client, "accessibility-teacher@example.com", "teacher")
    first = register(client, "accessibility-first@example.com", "student")
    second = register(client, "accessibility-second@example.com", "student")
    session_id = create_lecture(client, teacher)["session_id"]
    join_lecture(client, session_id, first)
    join_lecture(client, session_id, second)

    first_default = get_preference(
        client, session_id, first["access_token"]
    )
    second_default = get_preference(
        client, session_id, second["access_token"]
    )
    assert first_default["mode"] == "standard"
    assert first_default["translation_language"] == "kn"
    assert second_default["mode"] == "standard"

    save_preference(
        client, session_id, first["access_token"], "simplified"
    )
    assert get_preference(
        client, session_id, second["access_token"]
    )["mode"] == "standard"

    save_preference(
        client,
        session_id,
        second["access_token"],
        "translation",
        "hi",
    )
    save_preference(
        client, session_id, first["access_token"], "sign_support"
    )

    first_token = login(client, "accessibility-first@example.com")
    second_token = login(client, "accessibility-second@example.com")
    persisted_first = get_preference(client, session_id, first_token)
    persisted_second = get_preference(client, session_id, second_token)

    assert persisted_first["student_id"] == first["user"]["id"]
    assert persisted_first["session_id"] == session_id
    assert persisted_first["mode"] == "sign_support"
    assert persisted_second["student_id"] == second["user"]["id"]
    assert persisted_second["session_id"] == session_id
    assert persisted_second["mode"] == "translation"
    assert persisted_second["translation_language"] == "hi"

    connection = database.connect_db()
    try:
        rows = connection.execute(
            """
            SELECT student_id, session_id, mode, translation_language
            FROM student_accessibility_preferences
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchall()
    finally:
        connection.close()
    assert len(rows) == 2
    assert {
        (row["student_id"], row["mode"], row["translation_language"])
        for row in rows
    } == {
        (first["user"]["id"], "sign_support", "kn"),
        (second["user"]["id"], "translation", "hi"),
    }


def test_preferences_require_a_joined_student_and_validate_input(client):
    teacher = register(client, "accessibility-guard-teacher@example.com", "teacher")
    student = register(client, "accessibility-guard-student@example.com", "student")
    session_id = create_lecture(client, teacher)["session_id"]
    endpoint = f"/api/sessions/{session_id}/accessibility"

    assert client.get(endpoint).status_code == 401
    assert client.get(
        endpoint, headers=auth_header(teacher["access_token"])
    ).status_code == 403
    assert client.get(
        endpoint, headers=auth_header(student["access_token"])
    ).status_code == 403
    assert client.post(
        endpoint,
        headers=auth_header(student["access_token"]),
        json={"mode": "standard"},
    ).status_code == 403

    join_lecture(client, session_id, student)
    headers = auth_header(student["access_token"])
    assert client.post(
        endpoint, headers=headers, json={"mode": "karaoke"}
    ).status_code == 422
    assert client.post(
        endpoint,
        headers=headers,
        json={"mode": "translation", "translation_language": "en"},
    ).status_code == 422
    assert client.get(
        "/api/sessions/UNKNOWN/accessibility", headers=headers
    ).status_code == 404
