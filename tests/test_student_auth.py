from datetime import timedelta
import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.core.config import settings
from app.core.security import create_student_access_token


def test_student_registration_returns_token(client: TestClient):
    """1. Student registration returns access_token and student profile."""
    res = client.post("/api/students/register", json={
        "name": "Radha Raman",
        "registration_number": "SEC001",
        "branch": "CSE",
        "phone": "+919876549001",
        "email": "raman@college.edu"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["student"]["id"] is not None
    assert data["student"]["name"] == "Radha Raman"
    assert data["student"]["registration_number"] == "SEC001"


def test_student_token_claims_are_minimal_and_safe(client: TestClient):
    """2. Student token contains only safe identity claims without phone/email."""
    res = client.post("/api/students/register", json={
        "name": "Safe Token Student",
        "registration_number": "SEC002",
        "branch": "IT",
        "phone": "+919876549002",
        "email": "safetoken@college.edu"
    })
    token = res.json()["access_token"]
    student_id = res.json()["student"]["id"]

    # Decode without verifying to inspect payload
    unverified = jwt.decode(token, options={"verify_signature": False})
    assert unverified["sub"] == f"student:{student_id}"
    assert unverified["type"] == "student"
    assert "exp" in unverified
    assert "iat" in unverified

    # Ensure no sensitive PII is in token
    assert "phone" not in unverified
    assert "email" not in unverified
    assert "+919876549002" not in str(unverified)
    assert "safetoken@college.edu" not in str(unverified)


def test_student_token_cannot_access_admin_routes(client: TestClient):
    """3. Student token cannot be used as an Admin token."""
    reg = client.post("/api/students/register", json={
        "name": "Imposter Student",
        "registration_number": "SEC003",
        "branch": "CSE",
        "phone": "+919876549003",
        "email": "imposter@college.edu"
    }).json()

    headers = {"Authorization": f"Bearer {reg['access_token']}"}
    res = client.get("/api/admin/questions", headers=headers)
    assert res.status_code == 401
    assert "INVALID_ADMIN_CREDENTIALS" in res.json()["error_code"] or "INVALID_TOKEN" in res.json()["error_code"]


def test_admin_token_cannot_access_student_routes(client: TestClient, admin_auth_headers: dict):
    """4. Admin token cannot be used as a Student token."""
    res = client.get("/api/students/me", headers=admin_auth_headers)
    assert res.status_code == 401
    assert "INVALID_STUDENT_TOKEN" in res.json()["error_code"] or "INVALID_STUDENT_CLAIMS" in res.json()["error_code"]


def test_student_me_endpoint(client: TestClient):
    """5. Authenticated student can retrieve their own profile via /me."""
    reg = client.post("/api/students/register", json={
        "name": "Me Profile Student",
        "registration_number": "SEC004",
        "branch": "ECE",
        "phone": "+919876549004",
        "email": "me.profile@college.edu"
    }).json()

    headers = {"Authorization": f"Bearer {reg['access_token']}"}
    res = client.get("/api/students/me", headers=headers)
    assert res.status_code == 200
    profile = res.json()
    assert profile["id"] == reg["student"]["id"]
    assert profile["name"] == "Me Profile Student"
    assert profile["registration_number"] == "SEC004"


def test_invalid_and_expired_student_tokens(client: TestClient):
    """6 & 7. Invalid and expired student tokens are rejected with 401."""
    # Invalid token
    res_inv = client.get("/api/students/me", headers={"Authorization": "Bearer fake.student.token"})
    assert res_inv.status_code == 401

    # Expired token
    expired = create_student_access_token(student_id=1, expires_delta=timedelta(seconds=-10))
    res_exp = client.get("/api/students/me", headers={"Authorization": f"Bearer {expired}"})
    assert res_exp.status_code == 401
    assert res_exp.json()["error_code"] == "STUDENT_TOKEN_EXPIRED"


def test_authenticated_answer_submission_and_ownership(client: TestClient, admin_auth_headers: dict):
    """8, 9, 10, 11. Answer submission uses authenticated student identity and rejects spoofed fields."""
    # 1. Register student
    reg = client.post("/api/students/register", json={
        "name": "Answering Student",
        "registration_number": "SEC005",
        "branch": "CSE",
        "phone": "+919876549005",
        "email": "answerer@college.edu"
    }).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    # 2. Admin creates question and starts round
    q = client.post("/api/admin/questions", json={
        "question_text": "Security test question?",
        "option_a": "Correct A",
        "option_b": "Option B",
        "option_c": "Option C",
        "option_d": "Option D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    # 3. Unauthenticated answer submission -> 401
    unauth_res = client.post("/api/quiz/answers", json={"selected_option": "A"})
    assert unauth_res.status_code == 401

    # 4. Attempting to inject student_id or extra fields in request body -> 422 Unprocessable Entity
    spoofed_payload = {
        "student_id": 9999,
        "selected_option": "A"
    }
    spoof_res = client.post("/api/quiz/answers", json=spoofed_payload, headers=headers)
    assert spoof_res.status_code == 422

    # 5. Legitimate authenticated answer submission
    valid_payload = {"selected_option": "A"}
    valid_res = client.post("/api/quiz/answers", json=valid_payload, headers=headers)
    assert valid_res.status_code == 201
    ans_data = valid_res.json()
    # Backend derives student_id from token
    assert ans_data["student_id"] == reg["student"]["id"]
    assert ans_data["is_correct"] is True
    assert ans_data["response_time_ms"] >= 0

    # 6. Duplicate answer submission -> 409
    dup_res = client.post("/api/quiz/answers", json=valid_payload, headers=headers)
    assert dup_res.status_code == 409
    assert dup_res.json()["error_code"] == "DUPLICATE_ANSWER"


def test_websocket_token_authentication(client: TestClient, admin_auth_headers: dict):
    """14, 15, 16. WebSocket token authentication and raw student_id rejection."""
    reg = client.post("/api/students/register", json={
        "name": "WS Auth Student",
        "registration_number": "SEC006",
        "branch": "CSE",
        "phone": "+919876549006",
        "email": "wsauth@college.edu"
    }).json()

    token = reg["access_token"]
    student_id = reg["student"]["id"]

    # 1. Connecting with valid token succeeds
    with client.websocket_connect(f"/api/ws/quiz?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "quiz_state"

    # 2. Connecting with raw student_id is rejected (code 1008)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/ws/quiz?student_id={student_id}"):
            pass
    assert exc_info.value.code == 1008

    # 3. Connecting with invalid token is rejected (code 1008)
    with pytest.raises(WebSocketDisconnect) as exc_info2:
        with client.websocket_connect("/api/ws/quiz?token=invalid.jwt.token"):
            pass
    assert exc_info2.value.code == 1008


def test_student_list_is_admin_protected_and_not_public(client: TestClient, admin_auth_headers: dict):
    """18. Public student listing is restricted to Admin to protect participant privacy."""
    # Unauthenticated query to /api/students -> 401
    unauth_res = client.get("/api/students")
    assert unauth_res.status_code == 401

    # Student token query to /api/students -> 401
    reg = client.post("/api/students/register", json={
        "name": "Non Admin Student",
        "registration_number": "SEC007",
        "branch": "CSE",
        "phone": "+919876549007",
        "email": "nonadmin@college.edu"
    }).json()
    student_headers = {"Authorization": f"Bearer {reg['access_token']}"}
    student_res = client.get("/api/students", headers=student_headers)
    assert student_res.status_code == 401

    # Admin query -> 200 OK
    admin_res = client.get("/api/students", headers=admin_auth_headers)
    assert admin_res.status_code == 200
    assert isinstance(admin_res.json(), list)


def test_leaderboard_does_not_expose_phone_or_email(client: TestClient, admin_auth_headers: dict):
    """19. Leaderboard responses omit phone and email."""
    reg = client.post("/api/students/register", json={
        "name": "Privacy Student",
        "registration_number": "SEC008",
        "branch": "CSE",
        "phone": "+919876549008",
        "email": "privacy@college.edu"
    }).json()
    student_headers = {"Authorization": f"Bearer {reg['access_token']}"}

    q = client.post("/api/admin/questions", json={
        "question_text": "Privacy question?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    # Student submits answer
    client.post("/api/quiz/answers", json={"selected_option": "A"}, headers=student_headers)

    # Fetch leaderboard (public)
    lb_res = client.get(f"/api/quiz/rounds/{r['id']}/leaderboard")
    assert lb_res.status_code == 200
    lb_text = lb_res.text

    assert "+919876549008" not in lb_text
    assert "privacy@college.edu" not in lb_text
    assert "phone" not in lb_res.json()["all_entries"][0]
    assert "email" not in lb_res.json()["all_entries"][0]
