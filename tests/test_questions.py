from fastapi.testclient import TestClient


def test_admin_create_question(client: TestClient, admin_auth_headers: dict):
    payload = {
        "question_text": "In which city was Lord Krishna born?",
        "option_a": "Ayodhya",
        "option_b": "Mathura",
        "option_c": "Vrindavan",
        "option_d": "Dwarka",
        "correct_option": "B",
        "is_active": True,
    }
    response = client.post("/api/admin/questions", json=payload, headers=admin_auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["question_text"] == "In which city was Lord Krishna born?"
    assert data["correct_option"] == "B"


def test_admin_list_and_update_question(client: TestClient, admin_auth_headers: dict):
    payload = {
        "question_text": "What is the name of Lord Krishna's conch?",
        "option_a": "Panchajanya",
        "option_b": "Devadatta",
        "option_c": "Anantavijaya",
        "option_d": "Poundra",
        "correct_option": "A",
        "is_active": True,
    }
    created = client.post("/api/admin/questions", json=payload, headers=admin_auth_headers).json()
    q_id = created["id"]

    # List questions
    list_res = client.get("/api/admin/questions", headers=admin_auth_headers)
    assert list_res.status_code == 200
    assert any(q["id"] == q_id for q in list_res.json())

    # Update question
    update_payload = {"question_text": "What conch did Lord Krishna blow?"}
    update_res = client.put(f"/api/admin/questions/{q_id}", json=update_payload, headers=admin_auth_headers)
    assert update_res.status_code == 200
    assert update_res.json()["question_text"] == "What conch did Lord Krishna blow?"


def test_admin_deactivate_question(client: TestClient, admin_auth_headers: dict):
    payload = {
        "question_text": "Who was the foster mother of Lord Krishna?",
        "option_a": "Devaki",
        "option_b": "Yashoda",
        "option_c": "Rohini",
        "option_d": "Kunti",
        "correct_option": "B",
        "is_active": True,
    }
    created = client.post("/api/admin/questions", json=payload, headers=admin_auth_headers).json()
    q_id = created["id"]

    del_res = client.delete(f"/api/admin/questions/{q_id}", headers=admin_auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False
