import time
from fastapi.testclient import TestClient


def test_student_full_journey_e2e(client: TestClient, admin_auth_headers: dict):
    """
    Simulates the exact end-to-end multi-student live quiz journey:
    1. Student A and Student B register.
    2. Both open live WebSockets and see 'waiting'.
    3. Admin starts Question 1 -> Both receive 'question_started' live.
    4. Student A and B submit answers with their own tokens.
    5. Admin ends Question 1 -> Both receive 'round_ended' live.
    6. Both load Question 1 leaderboard.
    7. Admin starts Question 2 -> Both receive 'question_started' live.
    8. Student B answers correctly and fastest -> Round 2 independent leaderboard.
    9. Session restoration via /api/students/me verified.
    """
    # 1. Registration
    reg_a = client.post("/api/students/register", json={
        "name": "Rahul Verma",
        "registration_number": "2024CS001",
        "branch": "Computer Science & Engg",
        "phone": "9876543210",
        "email": "rahul@college.edu"
    }).json()
    token_a = reg_a["access_token"]
    student_a_id = reg_a["student"]["id"]

    reg_b = client.post("/api/students/register", json={
        "name": "Priya Sharma",
        "registration_number": "2024IT002",
        "branch": "Information Technology",
        "phone": "9876543211",
        "email": "priya@college.edu"
    }).json()
    token_b = reg_b["access_token"]
    student_b_id = reg_b["student"]["id"]

    # 2. Admin creates Questions
    q1 = client.post("/api/admin/questions", json={
        "question_text": "Which festival celebrates the appearance of Lord Krishna?",
        "option_a": "Diwali",
        "option_b": "Janmashtami",
        "option_c": "Holi",
        "option_d": "Rath Yatra",
        "correct_option": "B",
        "is_active": True
    }, headers=admin_auth_headers).json()

    q2 = client.post("/api/admin/questions", json={
        "question_text": "What was the name of Lord Krishna's conch shell?",
        "option_a": "Panchajanya",
        "option_b": "Devadatta",
        "option_c": "Paundra",
        "option_d": "Anantavijaya",
        "correct_option": "A",
        "is_active": True
    }, headers=admin_auth_headers).json()

    # 3. Open WebSocket for Student A and Student B
    with client.websocket_connect(f"/api/ws/quiz?token={token_a}") as ws_a:
        init_a = ws_a.receive_json()
        assert init_a["type"] == "quiz_state"
        assert init_a["data"]["status"] == "waiting"

        with client.websocket_connect(f"/api/ws/quiz?token={token_b}") as ws_b:
            init_b = ws_b.receive_json()
            assert init_b["type"] == "quiz_state"
            assert init_b["data"]["status"] == "waiting"

            # 4. Admin starts Question 1
            r1 = client.post("/api/admin/rounds/start", json={"question_id": q1["id"]}, headers=admin_auth_headers).json()
            r1_id = r1["id"]

            # Both receive question_started live
            ev1_a = ws_a.receive_json()
            ev1_b = ws_b.receive_json()
            assert ev1_a["type"] == "question_started"
            assert ev1_b["type"] == "question_started"
            assert ev1_a["data"]["question"]["question_text"] == "Which festival celebrates the appearance of Lord Krishna?"
            assert "correct_option" not in ev1_a["data"]["question"]

            # 5. Student A submits answer (Correct)
            time.sleep(0.01)
            ans_a1 = client.post(
                "/api/quiz/answers",
                json={"selected_option": "B"},
                headers={"Authorization": f"Bearer {token_a}"}
            )
            assert ans_a1.status_code == 201
            assert ans_a1.json()["is_correct"] is True

            # Student B submits answer (Incorrect)
            time.sleep(0.01)
            ans_b1 = client.post(
                "/api/quiz/answers",
                json={"selected_option": "A"},
                headers={"Authorization": f"Bearer {token_b}"}
            )
            assert ans_b1.status_code == 201
            assert ans_b1.json()["is_correct"] is False

            # 6. Admin ends Round 1
            end1 = client.post(f"/api/admin/rounds/{r1_id}/end", headers=admin_auth_headers)
            assert end1.status_code == 200

            # Both receive round_ended live
            ended_a1 = ws_a.receive_json()
            ended_b1 = ws_b.receive_json()
            assert ended_a1["type"] == "round_ended"
            assert ended_b1["type"] == "round_ended"

            # 7. Fetch Round 1 Leaderboard
            lb1 = client.get(f"/api/quiz/rounds/{r1_id}/leaderboard").json()
            assert lb1["total_submissions"] == 2
            assert lb1["total_correct"] == 1
            assert lb1["total_incorrect"] == 1
            assert lb1["top_5_winners"][0]["student_id"] == student_a_id
            assert lb1["top_5_winners"][0]["rank"] == 1
            # Student B has no rank
            assert lb1["all_entries"][1]["student_id"] == student_b_id
            assert lb1["all_entries"][1]["rank"] is None

            # 8. Admin starts Question 2 (Round 2)
            r2 = client.post("/api/admin/rounds/start", json={"question_id": q2["id"]}, headers=admin_auth_headers).json()
            r2_id = r2["id"]

            # Both receive question 2 live
            ev2_a = ws_a.receive_json()
            ev2_b = ws_b.receive_json()
            assert ev2_a["type"] == "question_started"
            assert ev2_b["type"] == "question_started"
            assert ev2_a["data"]["round_id"] == r2_id

            # 9. In Round 2: Student B answers correctly and fastest
            time.sleep(0.01)
            ans_b2 = client.post(
                "/api/quiz/answers",
                json={"selected_option": "A"},
                headers={"Authorization": f"Bearer {token_b}"}
            )
            assert ans_b2.status_code == 201
            assert ans_b2.json()["is_correct"] is True

            # Student A answers correctly later
            time.sleep(0.01)
            ans_a2 = client.post(
                "/api/quiz/answers",
                json={"selected_option": "A"},
                headers={"Authorization": f"Bearer {token_a}"}
            )
            assert ans_a2.status_code == 201
            assert ans_a2.json()["is_correct"] is True

            # Admin ends Round 2
            client.post(f"/api/admin/rounds/{r2_id}/end", headers=admin_auth_headers)

            # Round 2 Leaderboard: Student B is Rank #1 (independent ranking)
            lb2 = client.get(f"/api/quiz/rounds/{r2_id}/leaderboard").json()
            assert lb2["top_5_winners"][0]["student_id"] == student_b_id
            assert lb2["top_5_winners"][0]["rank"] == 1
            assert lb2["top_5_winners"][1]["student_id"] == student_a_id
            assert lb2["top_5_winners"][1]["rank"] == 2

    # 10. Session Restoration on Refresh
    me_res = client.get("/api/students/me", headers={"Authorization": f"Bearer {token_a}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Rahul Verma"
