import time
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.core.security import create_access_token
from app.core.config import settings


def test_complete_end_to_end_verification(client: TestClient, session: Session):
    # Create admin auth headers
    token = create_access_token(data={"sub": settings.ADMIN_USERNAME, "role": "admin"})
    admin_headers = {"Authorization": f"Bearer {token}"}

    # 3: Root & Health Check
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    # 4: Create student (public endpoint) -> receives profile & access_token
    s1_res = client.post("/api/students/register", json={
        "name": "E2E Student 1",
        "registration_number": "E2E_001",
        "branch": "CSE",
        "phone": "+919876500001",
        "email": "e2e_student1@college.edu"
    })
    assert s1_res.status_code == 201
    s1_data = s1_res.json()
    s1_headers = {"Authorization": f"Bearer {s1_data['access_token']}"}
    s1_id = s1_data["student"]["id"]

    s2_data = client.post("/api/students/register", json={
        "name": "E2E Student 2",
        "registration_number": "E2E_002",
        "branch": "IT",
        "phone": "+919876500002",
        "email": "e2e_student2@college.edu"
    }).json()
    s2_headers = {"Authorization": f"Bearer {s2_data['access_token']}"}
    s2_id = s2_data["student"]["id"]

    s3_data = client.post("/api/students/register", json={
        "name": "E2E Student 3",
        "registration_number": "E2E_003",
        "branch": "ECE",
        "phone": "+919876500003",
        "email": "e2e_student3@college.edu"
    }).json()
    s3_headers = {"Authorization": f"Bearer {s3_data['access_token']}"}
    s3_id = s3_data["student"]["id"]

    # 10: Test answering when there is no active round
    res_no_round = client.post("/api/quiz/answers", json={
        "selected_option": "A"
    }, headers=s1_headers)
    assert res_no_round.status_code == 400
    assert res_no_round.json()["error_code"] == "ROUND_NOT_ACTIVE"

    # 5: Test creating a question (Admin auth required)
    q1_res = client.post("/api/admin/questions", json={
        "question_text": "What is the divine weapon of Lord Krishna?",
        "option_a": "Sudarshana Chakra",
        "option_b": "Trishula",
        "option_c": "Gada",
        "option_d": "Brahmashira",
        "correct_option": "A",
        "is_active": True
    }, headers=admin_headers)
    assert q1_res.status_code == 201
    q1 = q1_res.json()
    assert q1["correct_option"] == "A"

    # 6: Test starting a quiz round (Admin auth required)
    r1_res = client.post("/api/admin/rounds/start", json={"question_id": q1["id"]}, headers=admin_headers)
    assert r1_res.status_code == 201
    r1 = r1_res.json()
    assert r1["status"] == "active"
    assert r1["started_at"] is not None

    # 11: Verify PublicQuestionResponse does NOT expose correct_option
    public_quiz = client.get("/api/quiz/active").json()
    assert public_quiz["is_active"] is True
    assert "correct_option" not in public_quiz["question"]
    assert public_quiz["question"]["question_text"] == "What is the divine weapon of Lord Krishna?"

    # 7 & 15: Multiple students answer: Student 1 submits correct answer (authenticated student)
    time.sleep(0.01)
    ans1 = client.post("/api/quiz/answers", json={
        "selected_option": "A"
    }, headers=s1_headers).json()
    assert ans1["is_correct"] is True
    assert ans1["student_id"] == s1_id
    assert ans1["response_time_ms"] >= 0

    # 8 & 15: Student 2 submits incorrect answer
    time.sleep(0.01)
    ans2 = client.post("/api/quiz/answers", json={
        "selected_option": "B"
    }, headers=s2_headers).json()
    assert ans2["is_correct"] is False
    assert ans2["student_id"] == s2_id

    # Student 3 submits correct answer slightly later
    time.sleep(0.01)
    ans3 = client.post("/api/quiz/answers", json={
        "selected_option": "A"
    }, headers=s3_headers).json()
    assert ans3["is_correct"] is True
    assert ans3["student_id"] == s3_id

    # 9: Test duplicate answer protection
    dup_ans = client.post("/api/quiz/answers", json={
        "selected_option": "A"
    }, headers=s1_headers)
    assert dup_ans.status_code == 409
    assert dup_ans.json()["error_code"] == "DUPLICATE_ANSWER"

    # 12 & 13: Test public leaderboard ordering and prize eligibility
    lb_r1 = client.get(f"/api/quiz/rounds/{r1['id']}/leaderboard").json()
    assert lb_r1["total_submissions"] == 3
    assert lb_r1["total_correct"] == 2
    assert lb_r1["total_incorrect"] == 1

    # Student 1 is rank 1, Student 3 is rank 2 (fastest response time first)
    assert lb_r1["top_5_winners"][0]["student_id"] == s1_id
    assert lb_r1["top_5_winners"][0]["rank"] == 1
    assert lb_r1["top_5_winners"][0]["is_top_5"] is True

    assert lb_r1["top_5_winners"][1]["student_id"] == s3_id
    assert lb_r1["top_5_winners"][1]["rank"] == 2
    assert lb_r1["top_5_winners"][1]["is_top_5"] is True

    # Student 2 (incorrect) must NOT be in top_5_winners or have a prize rank
    for winner in lb_r1["top_5_winners"]:
        assert winner["student_id"] != s2_id

    # 14: Test round independence: Round 2 starts fresh
    q2 = client.post("/api/admin/questions", json={
        "question_text": "Which river is associated with Lord Krishna's childhood in Gokul?",
        "option_a": "Ganga",
        "option_b": "Yamuna",
        "option_c": "Saraswati",
        "option_d": "Godavari",
        "correct_option": "B",
        "is_active": True
    }, headers=admin_headers).json()

    r2 = client.post("/api/admin/rounds/start", json={"question_id": q2["id"]}, headers=admin_headers).json()

    # In Round 2, Student 2 (who failed Round 1) answers correctly and first!
    ans_r2_s2 = client.post("/api/quiz/answers", json={
        "selected_option": "B"
    }, headers=s2_headers).json()
    assert ans_r2_s2["is_correct"] is True
    assert ans_r2_s2["student_id"] == s2_id

    # Check Round 2 leaderboard: Student 2 is #1
    lb_r2 = client.get(f"/api/quiz/rounds/{r2['id']}/leaderboard").json()
    assert lb_r2["top_5_winners"][0]["student_id"] == s2_id
    assert lb_r2["top_5_winners"][0]["rank"] == 1
    assert lb_r2["total_submissions"] == 1
