"""Authentication and persistent lecture-ownership API tests."""

from app import database


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, email, role="teacher"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "correct-horse-battery-staple",
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_login_and_password_is_hashed(client):
    account = register(client, "teacher@example.com")
    assert account["user"]["role"] == "teacher"
    assert "password" not in account
    assert "password_hash" not in account

    connection = database.connect_db()
    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            ("teacher@example.com",),
        ).fetchone()
    finally:
        connection.close()
    assert row["password_hash"].startswith("scrypt$")
    assert "correct-horse-battery-staple" not in row["password_hash"]

    login = client.post(
        "/api/auth/login",
        json={"email": "TEACHER@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "teacher@example.com"

    me = client.get("/api/auth/me", headers=auth_header(login.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "teacher"


def test_teacher_lecture_is_saved_with_owner_and_times(client):
    account = register(client, "owner@example.com")
    response = client.post(
        "/api/lectures",
        headers=auth_header(account["access_token"]),
        json={"title": "Python Functions"},
    )
    assert response.status_code == 201
    lecture = response.json()
    assert lecture["teacher_id"] == account["user"]["id"]
    assert lecture["title"] == "Python Functions"
    assert lecture["start_time"] == lecture["started_at"]
    assert lecture["end_time"] is None

    connection = database.connect_db()
    try:
        row = connection.execute(
            """
            SELECT session_id, teacher_id, title, start_time, end_time
            FROM sessions WHERE session_id = ?
            """,
            (lecture["session_id"],),
        ).fetchone()
    finally:
        connection.close()
    assert row["teacher_id"] == account["user"]["id"]
    assert row["title"] == "Python Functions"
    assert row["start_time"]
    assert row["end_time"] is None


def test_ending_authenticated_lecture_persists_end_time(client):
    account = register(client, "ending@example.com")
    created = client.post(
        "/api/lectures",
        headers=auth_header(account["access_token"]),
        json={"title": "Ending Time"},
    ).json()
    ended = client.post(f"/api/sessions/{created['session_id']}/end")
    assert ended.status_code == 200
    assert ended.json()["end_time"] == ended.json()["ended_at"]

    connection = database.connect_db()
    try:
        row = connection.execute(
            "SELECT end_time FROM sessions WHERE session_id = ?",
            (created["session_id"],),
        ).fetchone()
    finally:
        connection.close()
    assert row["end_time"]


def test_only_teacher_can_create_authenticated_lecture(client):
    student = register(client, "student@example.com", role="student")
    response = client.post(
        "/api/lectures",
        headers=auth_header(student["access_token"]),
        json={"title": "Not allowed"},
    )
    assert response.status_code == 403


def test_wrong_password_and_missing_token_are_rejected(client):
    register(client, "secure@example.com")
    wrong = client.post(
        "/api/auth/login",
        json={"email": "secure@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/lectures", json={"title": "No login"}).status_code == 401
