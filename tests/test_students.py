from fastapi.testclient import TestClient


def test_register_student_success(client: TestClient):
    payload = {
        "name": "Arjun Sharma",
        "registration_number": "2024CS101",
        "branch": "Computer Science",
        "phone": "+919876543210",
        "email": "arjun.sharma@gmail.com",
    }
    response = client.post("/api/students/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["student"]["id"] is not None
    assert data["student"]["name"] == "Arjun Sharma"
    assert data["student"]["registration_number"] == "2024CS101"
    assert data["student"]["email"] == "arjun.sharma@gmail.com"


def test_register_student_idempotent(client: TestClient):
    payload = {
        "name": "Radha Rani",
        "registration_number": "2024IT102",
        "branch": "Information Technology",
        "phone": "+919876543211",
        "email": "radha.rani@gmail.com",
    }
    res1 = client.post("/api/students/register", json=payload)
    assert res1.status_code == 201
    student_id = res1.json()["student"]["id"]
    token1 = res1.json()["access_token"]
    assert token1 is not None

    # Re-registering with identical info returns existing student and valid token
    res2 = client.post("/api/students/register", json=payload)
    assert res2.status_code == 201
    assert res2.json()["student"]["id"] == student_id
    assert "access_token" in res2.json()


def test_register_student_conflict_different_email(client: TestClient):
    payload1 = {
        "name": "Krishna Das",
        "registration_number": "2024EE103",
        "branch": "Electrical",
        "phone": "+919876543212",
        "email": "krishna.das@gmail.com",
    }
    client.post("/api/students/register", json=payload1)

    # Same registration number with different email
    payload2 = {
        "name": "Krishna Das",
        "registration_number": "2024EE103",
        "branch": "Electrical",
        "phone": "+919876543212",
        "email": "another.email@gmail.com",
    }
    res2 = client.post("/api/students/register", json=payload2)
    assert res2.status_code == 409
    assert "already registered with a different email" in res2.json()["detail"]


def test_register_student_validation_errors(client: TestClient):
    # Invalid email
    bad_payload = {
        "name": "Test User",
        "registration_number": "REG001",
        "branch": "CS",
        "phone": "1234567890",
        "email": "not-an-email",
    }
    res = client.post("/api/students/register", json=bad_payload)
    assert res.status_code == 422

    # Blank name
    blank_name_payload = {
        "name": "   ",
        "registration_number": "REG002",
        "branch": "CS",
        "phone": "1234567890",
        "email": "valid@gmail.com",
    }
    res2 = client.post("/api/students/register", json=blank_name_payload)
    assert res2.status_code == 422


def test_get_student_by_id(client: TestClient, admin_auth_headers: dict):
    payload = {
        "name": "Gopal Verma",
        "registration_number": "2024ME104",
        "branch": "Mechanical",
        "phone": "+919876543213",
        "email": "gopal.verma@gmail.com",
    }
    created = client.post("/api/students/register", json=payload).json()
    student_id = created["student"]["id"]

    res = client.get(f"/api/students/{student_id}", headers=admin_auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Gopal Verma"

    # Non-existent student
    res_404 = client.get("/api/students/99999", headers=admin_auth_headers)
    assert res_404.status_code == 404
