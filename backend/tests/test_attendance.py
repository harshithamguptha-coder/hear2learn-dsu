"""Persistent Student attendance and lecture-history API tests."""

from app import database


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, email, role):
    response = client.post(
        "/api/auth/register",
        json={
            "name": f"{role.title()} User",
            "email": email,
            "password": "attendance-password-123",
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_lecture(client, teacher):
    response = client.post(
        "/api/lectures",
        headers=auth_header(teacher["access_token"]),
        json={"title": "Attendance Lecture"},
    )
    assert response.status_code == 201
    return response.json()


def test_student_attendance_persists_after_leave_and_login(client):
    teacher = register(client, "attendance-teacher@example.com", "teacher")
    student = register(client, "attendance-student@example.com", "student")
    lecture = create_lecture(client, teacher)
    session_id = lecture["session_id"]

    joined = client.post(
        f"/api/sessions/{session_id}/attendance/join",
        headers=auth_header(student["access_token"]),
    )
    assert joined.status_code == 201
    assert joined.json()["student_id"] == student["user"]["id"]
    assert joined.json()["session_id"] == session_id
    assert joined.json()["left_at"] is None

    history = client.get(
        "/api/my-lectures",
        headers=auth_header(student["access_token"]),
    )
    assert history.status_code == 200
    assert history.json()[0]["title"] == "Attendance Lecture"
    assert history.json()[0]["teacher"] == "Teacher User"
    assert history.json()[0]["status"] == "in_progress"

    left = client.post(
        f"/api/sessions/{session_id}/attendance/leave",
        headers=auth_header(student["access_token"]),
    )
    assert left.status_code == 200
    assert left.json()["left_at"]

    login = client.post(
        "/api/auth/login",
        json={
            "email": "attendance-student@example.com",
            "password": "attendance-password-123",
        },
    )
    assert login.status_code == 200
    after_login = client.get(
        "/api/my-lectures",
        headers=auth_header(login.json()["access_token"]),
    )
    assert after_login.status_code == 200
    assert len(after_login.json()) == 1
    assert after_login.json()[0]["status"] == "attended"
    assert after_login.json()[0]["left_at"]


def test_attendance_history_is_private_to_each_student(client):
    teacher = register(client, "private-teacher@example.com", "teacher")
    first_student = register(client, "first-student@example.com", "student")
    second_student = register(client, "second-student@example.com", "student")
    lecture = create_lecture(client, teacher)

    assert client.post(
        f"/api/sessions/{lecture['session_id']}/attendance/join",
        headers=auth_header(first_student["access_token"]),
    ).status_code == 201

    first_history = client.get(
        "/api/my-lectures",
        headers=auth_header(first_student["access_token"]),
    )
    second_history = client.get(
        "/api/my-lectures",
        headers=auth_header(second_student["access_token"]),
    )
    assert len(first_history.json()) == 1
    assert second_history.json() == []


def test_teacher_end_closes_open_attendance(client):
    teacher = register(client, "ending-teacher@example.com", "teacher")
    student = register(client, "ending-student@example.com", "student")
    lecture = create_lecture(client, teacher)
    session_id = lecture["session_id"]
    client.post(
        f"/api/sessions/{session_id}/attendance/join",
        headers=auth_header(student["access_token"]),
    )
    ended = client.post(f"/api/sessions/{session_id}/end")
    assert ended.status_code == 200

    history = client.get(
        "/api/my-lectures",
        headers=auth_header(student["access_token"]),
    ).json()[0]
    assert history["status"] == "attended"
    assert history["left_at"] == ended.json()["end_time"]


def test_attendance_requires_a_student_token(client):
    teacher = register(client, "guard-teacher@example.com", "teacher")
    lecture = create_lecture(client, teacher)
    assert client.post(
        f"/api/sessions/{lecture['session_id']}/attendance/join"
    ).status_code == 401
    assert client.post(
        f"/api/sessions/{lecture['session_id']}/attendance/join",
        headers=auth_header(teacher["access_token"]),
    ).status_code == 403
    assert client.get("/api/my-lectures").status_code == 401
