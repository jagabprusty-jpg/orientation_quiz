from datetime import timedelta
import jwt
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.security import create_access_token


def test_admin_login_success(client: TestClient):
    """1. Successful admin login."""
    response = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"

    # Decode token to verify claims
    decoded = jwt.decode(
        data["access_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    assert decoded["sub"] == "admin"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_admin_login_invalid_username(client: TestClient):
    """2. Invalid username."""
    response = client.post("/api/admin/auth/login", json={
        "username": "wrong_user",
        "password": "admin123",
    })
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"
    assert "Invalid username or password" in response.json()["detail"]


def test_admin_login_invalid_password(client: TestClient):
    """3. Invalid password."""
    response = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "wrong_password",
    })
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"
    assert "Invalid username or password" in response.json()["detail"]


def test_auth_me_endpoint(client: TestClient, admin_auth_headers: dict):
    """Verify /api/admin/auth/me with valid token."""
    response = client.get("/api/admin/auth/me", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_missing_auth_header(client: TestClient):
    """4. Missing Authorization header."""
    response = client.get("/api/admin/questions")
    assert response.status_code == 401
    assert response.json()["error_code"] == "TOKEN_MISSING"


def test_invalid_token(client: TestClient):
    """5. Invalid token signature/format."""
    headers = {"Authorization": "Bearer invalid.token.payload"}
    response = client.get("/api/admin/questions", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"


def test_expired_token(client: TestClient):
    """6. Expired token."""
    expired_token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(seconds=-10)
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/admin/questions", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "TOKEN_EXPIRED"


def test_malformed_bearer_token(client: TestClient):
    """7. Malformed Bearer token."""
    headers = {"Authorization": "Basic some_basic_auth_token"}
    response = client.get("/api/admin/questions", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_SCHEME"


def test_successful_authenticated_admin_request(client: TestClient, admin_auth_headers: dict):
    """8. Successful authenticated admin request."""
    response = client.get("/api/admin/questions", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unauthenticated_request_to_create_question_401(client: TestClient):
    """9. Unauthenticated request to create question -> 401."""
    payload = {
        "question_text": "Sample Question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }
    response = client.post("/api/admin/questions", json=payload)
    assert response.status_code == 401


def test_unauthenticated_request_to_start_round_401(client: TestClient):
    """10. Unauthenticated request to start round -> 401."""
    response = client.post("/api/admin/rounds/start", json={"question_id": 1})
    assert response.status_code == 401


def test_unauthenticated_request_to_end_round_401(client: TestClient):
    """11. Unauthenticated request to end round -> 401."""
    response = client.post("/api/admin/rounds/1/end")
    assert response.status_code == 401


def test_authenticated_admin_question_crud(client: TestClient, admin_auth_headers: dict):
    """12. Authenticated admin can create, update, and deactivate questions."""
    # Create
    create_res = client.post("/api/admin/questions", json={
        "question_text": "Who is the eternal consort of Lord Krishna?",
        "option_a": "Radharani",
        "option_b": "Satyabhama",
        "option_c": "Rukmini",
        "option_d": "Kalindi",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers)
    assert create_res.status_code == 201
    q_id = create_res.json()["id"]

    # Update
    update_res = client.put(f"/api/admin/questions/{q_id}", json={
        "question_text": "Who is the foremost devotee and consort of Lord Krishna?",
    }, headers=admin_auth_headers)
    assert update_res.status_code == 200
    assert "foremost devotee" in update_res.json()["question_text"]

    # Deactivate
    del_res = client.delete(f"/api/admin/questions/{q_id}", headers=admin_auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False


def test_authenticated_admin_round_lifecycle(client: TestClient, admin_auth_headers: dict):
    """13. Authenticated admin can start and end rounds."""
    # Create question
    q = client.post("/api/admin/questions", json={
        "question_text": "Where did Krishna deliver the Bhagavad Gita?",
        "option_a": "Kurukshetra",
        "option_b": "Vrindavan",
        "option_c": "Hastinapur",
        "option_d": "Indraprastha",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # Start round
    start_res = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers)
    assert start_res.status_code == 201
    r_id = start_res.json()["id"]

    # End round
    end_res = client.post(f"/api/admin/rounds/{r_id}/end", headers=admin_auth_headers)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "ended"


def test_public_endpoints_work_without_admin_auth(client: TestClient, admin_auth_headers: dict):
    """14. Public student endpoints work without admin authentication."""
    # 1. Register student without admin auth headers -> receives student token
    student_res = client.post("/api/students/register", json={
        "name": "Public Student",
        "registration_number": "PUB001",
        "branch": "CSE",
        "phone": "+919876540001",
        "email": "public.student@college.edu"
    })
    assert student_res.status_code == 201
    student_data = student_res.json()
    student_headers = {"Authorization": f"Bearer {student_data['access_token']}"}

    # 2. Admin starts round (requires admin auth)
    q = client.post("/api/admin/questions", json={
        "question_text": "What is Krishna's favourite butter called?",
        "option_a": "Ghee",
        "option_b": "Makhan",
        "option_c": "Paneer",
        "option_d": "Malai",
        "correct_option": "B",
        "is_active": True,
    }, headers=admin_auth_headers).json()
    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    # 3. Student queries active quiz without any auth header (public endpoint)
    active_res = client.get("/api/quiz/active")
    assert active_res.status_code == 200
    assert active_res.json()["is_active"] is True
    assert "correct_option" not in active_res.json()["question"]

    # 4. Student submits answer with student token (not admin token)
    ans_res = client.post(
        f"/api/quiz/rounds/{r['id']}/answers",
        json={"selected_option": "B"},
        headers=student_headers
    )
    assert ans_res.status_code == 201
    assert ans_res.json()["is_correct"] is True

    # 5. Public leaderboard query without any auth header
    lb_res = client.get(f"/api/quiz/rounds/{r['id']}/leaderboard")
    assert lb_res.status_code == 200
    assert lb_res.json()["total_submissions"] == 1


def test_jwt_never_contains_password_or_hash(client: TestClient):
    """15. JWT token payload never contains plaintext password or password hash."""
    login_res = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    token = login_res.json()["access_token"]
    unverified_payload = jwt.decode(token, options={"verify_signature": False})

    assert "password" not in unverified_payload
    assert "admin123" not in str(unverified_payload)
    assert settings.ADMIN_PASSWORD_HASH not in str(unverified_payload)
    assert settings.JWT_SECRET_KEY not in str(unverified_payload)


def test_api_responses_never_expose_secrets_or_password_hashes(client: TestClient, admin_auth_headers: dict):
    """16. API responses never expose password hashes or JWT secrets."""
    login_res = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    assert settings.ADMIN_PASSWORD_HASH not in login_res.text
    assert settings.JWT_SECRET_KEY not in login_res.text

    me_res = client.get("/api/admin/auth/me", headers=admin_auth_headers)
    assert settings.ADMIN_PASSWORD_HASH not in me_res.text
    assert "password" not in me_res.json()
