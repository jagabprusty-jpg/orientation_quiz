import time
from fastapi.testclient import TestClient


def test_leaderboard_ranking_and_top_5_flag(client: TestClient, admin_auth_headers: dict):
    # 1. Create Question
    q = client.post("/api/admin/questions", json={
        "question_text": "On which tithi is Janmashtami celebrated?",
        "option_a": "Ashtami",
        "option_b": "Navami",
        "option_c": "Dashami",
        "option_d": "Ekadashi",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # 2. Start Round
    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()
    round_id = r["id"]

    # 3. Create 7 students
    student_headers_list = []
    student_ids = []
    for i in range(1, 8):
        s = client.post("/api/students/register", json={
            "name": f"Student {i}",
            "registration_number": f"REG_{i:03d}",
            "branch": "CSE",
            "phone": f"+9198765432{i:02d}",
            "email": f"student{i}@test.com",
        }).json()
        student_headers_list.append({"Authorization": f"Bearer {s['access_token']}"})
        student_ids.append(s["student"]["id"])

    # 4. Students 0..5 answer correctly with progressive slight delays
    for i in range(6):
        time.sleep(0.01)  # small delay to differentiate response time
        res = client.post(
            f"/api/quiz/rounds/{round_id}/answers",
            json={"selected_option": "A"},  # CORRECT
            headers=student_headers_list[i]
        )
        assert res.status_code == 201

    # 5. Student 6 answers incorrectly
    res_wrong = client.post(
        f"/api/quiz/rounds/{round_id}/answers",
        json={"selected_option": "B"},  # WRONG
        headers=student_headers_list[6]
    )
    assert res_wrong.status_code == 201

    # 6. Fetch public leaderboard
    lb_res = client.get(f"/api/quiz/rounds/{round_id}/leaderboard")
    assert lb_res.status_code == 200
    lb = lb_res.json()

    assert lb["total_submissions"] == 7
    assert lb["total_correct"] == 6
    assert lb["total_incorrect"] == 1
    assert len(lb["top_5_winners"]) == 5
    assert len(lb["ranked_correct_entries"]) == 6

    # Verify ranking 1 to 6
    for idx, entry in enumerate(lb["ranked_correct_entries"]):
        assert entry["rank"] == idx + 1
        assert entry["is_correct"] is True
        if idx < 5:
            assert entry["is_top_5"] is True
        else:
            assert entry["is_top_5"] is False

    # Verify fastest first ordering
    times = [e["response_time_ms"] for e in lb["ranked_correct_entries"]]
    assert times == sorted(times)

    # Verify incorrect answer is in all_entries but has rank=None and is_top_5=False
    wrong_entries = [e for e in lb["all_entries"] if not e["is_correct"]]
    assert len(wrong_entries) == 1
    assert wrong_entries[0]["rank"] is None
    assert wrong_entries[0]["is_top_5"] is False
    assert wrong_entries[0]["student_id"] == student_ids[6]


def test_independent_rounds_no_cumulative_score(client: TestClient, admin_auth_headers: dict):
    # Setup Student 1 and Student 2
    s1 = client.post("/api/students/register", json={
        "name": "Student Alpha",
        "registration_number": "ALPHA01",
        "branch": "CSE",
        "phone": "+919876543288",
        "email": "alpha@test.com",
    }).json()
    s1_headers = {"Authorization": f"Bearer {s1['access_token']}"}

    s2 = client.post("/api/students/register", json={
        "name": "Student Beta",
        "registration_number": "BETA01",
        "branch": "CSE",
        "phone": "+919876543289",
        "email": "beta@test.com",
    }).json()
    s2_headers = {"Authorization": f"Bearer {s2['access_token']}"}

    # Round 1: Correct option = A
    q1 = client.post("/api/admin/questions", json={
        "question_text": "Round 1 Question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r1 = client.post("/api/admin/rounds/start", json={"question_id": q1["id"]}, headers=admin_auth_headers).json()

    # Alpha gets it wrong, Beta gets it right
    client.post(f"/api/quiz/rounds/{r1['id']}/answers", json={"selected_option": "B"}, headers=s1_headers)
    client.post(f"/api/quiz/rounds/{r1['id']}/answers", json={"selected_option": "A"}, headers=s2_headers)

    # Round 1 Leaderboard: Beta is Rank 1, Alpha is unranked
    lb1 = client.get(f"/api/quiz/rounds/{r1['id']}/leaderboard").json()
    assert lb1["top_5_winners"][0]["student_id"] == s2["student"]["id"]

    # Round 2: Correct option = C
    q2 = client.post("/api/admin/questions", json={
        "question_text": "Round 2 Question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "C",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r2 = client.post("/api/admin/rounds/start", json={"question_id": q2["id"]}, headers=admin_auth_headers).json()

    # In Round 2: Alpha answers immediately (correct), Beta answers later (correct)
    client.post(f"/api/quiz/rounds/{r2['id']}/answers", json={"selected_option": "C"}, headers=s1_headers)
    time.sleep(0.01)
    client.post(f"/api/quiz/rounds/{r2['id']}/answers", json={"selected_option": "C"}, headers=s2_headers)

    # Round 2 Leaderboard: Alpha is now Rank 1! Completely fresh round.
    lb2 = client.get(f"/api/quiz/rounds/{r2['id']}/leaderboard").json()
    assert lb2["top_5_winners"][0]["student_id"] == s1["student"]["id"]
    assert lb2["top_5_winners"][0]["rank"] == 1
    assert lb2["top_5_winners"][1]["student_id"] == s2["student"]["id"]
    assert lb2["top_5_winners"][1]["rank"] == 2
