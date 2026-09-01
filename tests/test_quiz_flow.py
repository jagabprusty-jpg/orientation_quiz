from fastapi.testclient import TestClient


def test_quiz_flow_no_active_round(client: TestClient):
    res = client.get("/api/quiz/active")
    assert res.status_code == 200
    data = res.json()
    assert data["is_active"] is False
    assert data["round_id"] is None
    assert data["question"] is None


def test_quiz_round_start_and_public_question_security(client: TestClient, admin_auth_headers: dict):
    # 1. Create a question
    q_payload = {
        "question_text": "What is the name of Lord Krishna's bow?",
        "option_a": "Gandiva",
        "option_b": "Sharanga",
        "option_c": "Pinaka",
        "option_d": "Vijaya",
        "correct_option": "B",
        "is_active": True,
    }
    q_res = client.post("/api/admin/questions", json=q_payload, headers=admin_auth_headers)
    q_id = q_res.json()["id"]

    # 2. Admin starts the round
    round_res = client.post("/api/admin/rounds/start", json={"question_id": q_id}, headers=admin_auth_headers)
    assert round_res.status_code == 201
    round_data = round_res.json()
    assert round_data["status"] == "active"
    round_id = round_data["id"]

    # 3. Student queries active quiz without any admin headers
    active_res = client.get("/api/quiz/active")
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["is_active"] is True
    assert active_data["round_id"] == round_id
    assert active_data["question"]["id"] == q_id
    assert active_data["question"]["question_text"] == "What is the name of Lord Krishna's bow?"
    
    # CRITICAL: Verify correct_option is NOT exposed in public question response
    assert "correct_option" not in active_data["question"]


def test_student_answer_submission_correct_and_incorrect(client: TestClient, admin_auth_headers: dict):
    # 1. Register two students
    s1_res = client.post("/api/students/register", json={
        "name": "Student One",
        "registration_number": "REG1",
        "branch": "CS",
        "phone": "+919999999901",
        "email": "student1@college.edu",
    }).json()
    s1_headers = {"Authorization": f"Bearer {s1_res['access_token']}"}

    s2_res = client.post("/api/students/register", json={
        "name": "Student Two",
        "registration_number": "REG2",
        "branch": "EE",
        "phone": "+919999999902",
        "email": "student2@college.edu",
    }).json()
    s2_headers = {"Authorization": f"Bearer {s2_res['access_token']}"}

    # 2. Admin creates question (Correct option = C)
    q = client.post("/api/admin/questions", json={
        "question_text": "Who was the charioteer of Arjuna in the Kurukshetra war?",
        "option_a": "Bhishma",
        "option_b": "Drona",
        "option_c": "Lord Krishna",
        "option_d": "Karna",
        "correct_option": "C",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # 3. Admin starts round
    round_obj = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()
    round_id = round_obj["id"]

    # 4. Student 1 submits correct answer
    ans1_res = client.post(
        f"/api/quiz/rounds/{round_id}/answers",
        json={"selected_option": "C"},
        headers=s1_headers
    )
    assert ans1_res.status_code == 201
    ans1_data = ans1_res.json()
    assert ans1_data["is_correct"] is True
    assert ans1_data["response_time_ms"] >= 0

    # 5. Student 2 submits incorrect answer
    ans2_res = client.post(
        f"/api/quiz/rounds/{round_id}/answers",
        json={"selected_option": "A"},
        headers=s2_headers
    )
    assert ans2_res.status_code == 201
    ans2_data = ans2_res.json()
    assert ans2_data["is_correct"] is False
    assert ans2_data["response_time_ms"] >= 0

    # 6. Student 1 tries to submit again in the same round (Duplicate answer protection)
    dup_res = client.post(
        f"/api/quiz/rounds/{round_id}/answers",
        json={"selected_option": "C"},
        headers=s1_headers
    )
    assert dup_res.status_code == 409
    assert "already submitted" in dup_res.json()["detail"].lower()


def test_answer_submission_after_round_ended(client: TestClient, admin_auth_headers: dict):
    s_res = client.post("/api/students/register", json={
        "name": "Late Student",
        "registration_number": "LATE01",
        "branch": "ME",
        "phone": "+919999999903",
        "email": "late@college.edu",
    }).json()
    s_headers = {"Authorization": f"Bearer {s_res['access_token']}"}

    q = client.post("/api/admin/questions", json={
        "question_text": "Sample Question?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    round_obj = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()
    round_id = round_obj["id"]

    # Admin ends round
    client.post(f"/api/admin/rounds/{round_id}/end", headers=admin_auth_headers)

    # Submitting answer now should fail
    late_res = client.post(
        f"/api/quiz/rounds/{round_id}/answers",
        json={"selected_option": "A"},
        headers=s_headers
    )
    assert late_res.status_code == 400
    assert "ended" in late_res.json()["detail"].lower()


def test_starting_new_round_ends_previous_round(client: TestClient, admin_auth_headers: dict):
    q1 = client.post("/api/admin/questions", json={
        "question_text": "Question 1?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    q2 = client.post("/api/admin/questions", json={
        "question_text": "Question 2?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "B",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r1 = client.post("/api/admin/rounds/start", json={"question_id": q1["id"]}, headers=admin_auth_headers).json()
    assert r1["status"] == "active"

    # Start round 2
    r2 = client.post("/api/admin/rounds/start", json={"question_id": q2["id"]}, headers=admin_auth_headers).json()
    assert r2["status"] == "active"

    # Verify round 1 is now ended
    r1_check = client.get(f"/api/admin/rounds/{r1['id']}", headers=admin_auth_headers).json()
    assert r1_check["status"] == "ended"
    assert r1_check["ended_at"] is not None
