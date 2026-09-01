from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.answer import Answer
from app.models.enums import OptionEnum
from app.crud.answers import record_answer
from app.core.exceptions import DuplicateAnswerException
from datetime import datetime, timezone
import pytest


def test_database_level_unique_constraint_on_answer(session: Session, client: TestClient, admin_auth_headers: dict):
    # Register student
    s = client.post("/api/students/register", json={
        "name": "DB Constraint Test Student",
        "registration_number": "CONCURR001",
        "branch": "CSE",
        "phone": "+919111111111",
        "email": "concurr@test.com",
    }).json()
    student_id = s["student"]["id"]

    # Create question & round (requires admin auth)
    q = client.post("/api/admin/questions", json={
        "question_text": "Constraint Test Question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    now = datetime.now(timezone.utc)
    # First record_answer works
    ans1 = record_answer(
        session=session,
        round_id=r["id"],
        student_id=student_id,
        selected_option=OptionEnum.A,
        is_correct=True,
        response_time_ms=150,
        answered_at=now,
    )
    assert ans1.id is not None

    # Second direct record_answer fails with DuplicateAnswerException due to uniqueness check / constraint
    with pytest.raises(DuplicateAnswerException):
        record_answer(
            session=session,
            round_id=r["id"],
            student_id=student_id,
            selected_option=OptionEnum.B,
            is_correct=False,
            response_time_ms=200,
            answered_at=now,
        )


def test_payload_tampering_rejected_by_schema(client: TestClient, admin_auth_headers: dict):
    """Verify backend rejects requests with unexpected client-injected fields."""
    s = client.post("/api/students/register", json={
        "name": "Hacker Student",
        "registration_number": "HACK001",
        "branch": "CSE",
        "phone": "+919222222222",
        "email": "hacker@test.com",
    }).json()
    s_headers = {"Authorization": f"Bearer {s['access_token']}"}

    q = client.post("/api/admin/questions", json={
        "question_text": "Security Question",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "D",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    # Student attempts to inject is_correct=True and response_time_ms=1
    tampered_payload = {
        "selected_option": "A",
        "is_correct": True,
        "response_time_ms": 1,
    }

    res = client.post(f"/api/quiz/rounds/{r['id']}/answers", json=tampered_payload, headers=s_headers)
    # Extra forbidden fields cause 422 Unprocessable Entity
    assert res.status_code == 422

    # Legitimate payload
    legit_payload = {"selected_option": "A"}
    res_legit = client.post(f"/api/quiz/rounds/{r['id']}/answers", json=legit_payload, headers=s_headers)
    assert res_legit.status_code == 201
    assert res_legit.json()["is_correct"] is False
