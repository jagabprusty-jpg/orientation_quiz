import asyncio
import json
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.realtime.connection_manager import connection_manager
from app.realtime.events import QuestionStartedEvent, QuestionStartedData
from app.schemas.question import PublicQuestionResponse
from app.core.config import settings
from datetime import datetime, timezone


def test_student_ws_connect_success_waiting_state(client: TestClient):
    """1. Registered student connects with token and receives 'quiz_state' (waiting)."""
    student_res = client.post("/api/students/register", json={
        "name": "WS Student 1",
        "registration_number": "WS001",
        "branch": "CSE",
        "phone": "+919876541001",
        "email": "ws1@college.edu"
    }).json()
    token = student_res["access_token"]

    with client.websocket_connect(f"/api/ws/quiz?token={token}") as websocket:
        initial_msg = websocket.receive_json()
        assert initial_msg["type"] == "quiz_state"
        assert initial_msg["data"]["status"] == "waiting"
        assert initial_msg["data"]["question"] is None


def test_unknown_student_token_ws_connect_rejected(client: TestClient):
    """2. Non-existent student ID in token is rejected with policy violation (1008)."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/ws/quiz?token=invalid.jwt.token"):
            pass
    assert exc_info.value.code == 1008


def test_missing_token_ws_connect_rejected(client: TestClient):
    """3. Connection without token is rejected."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/ws/quiz"):
            pass
    assert exc_info.value.code == 1008


def test_student_reconnect_receives_active_question(client: TestClient, admin_auth_headers: dict):
    """4. Reconnecting student immediately receives active question."""
    # Register student
    student_res = client.post("/api/students/register", json={
        "name": "WS Student 2",
        "registration_number": "WS002",
        "branch": "IT",
        "phone": "+919876541002",
        "email": "ws2@college.edu"
    }).json()
    token = student_res["access_token"]

    # Admin creates question and starts round
    q = client.post("/api/admin/questions", json={
        "question_text": "What was the childhood village of Lord Krishna?",
        "option_a": "Gokul",
        "option_b": "Barsana",
        "option_c": "Nandgaon",
        "option_d": "Govardhan",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

    # Student connects now (simulating late join or reconnect)
    with client.websocket_connect(f"/api/ws/quiz?token={token}") as websocket:
        msg = websocket.receive_json()
        assert msg["type"] == "quiz_state"
        assert msg["data"]["status"] == "active"
        assert msg["data"]["round_id"] == r["id"]
        assert msg["data"]["question"]["id"] == q["id"]
        assert msg["data"]["question"]["question_text"] == "What was the childhood village of Lord Krishna?"
        # Verify security: no correct_option
        assert "correct_option" not in msg["data"]["question"]


def test_admin_start_and_end_round_broadcasts(client: TestClient, admin_auth_headers: dict):
    """5 & 6 & 7. Multiple students receive question_started and round_ended broadcasts."""
    # Register 2 students
    s1 = client.post("/api/students/register", json={
        "name": "WS Multi 1",
        "registration_number": "WSM001",
        "branch": "CSE",
        "phone": "+919876541003",
        "email": "wsm1@college.edu"
    }).json()
    token1 = s1["access_token"]

    s2 = client.post("/api/students/register", json={
        "name": "WS Multi 2",
        "registration_number": "WSM002",
        "branch": "ECE",
        "phone": "+919876541004",
        "email": "wsm2@college.edu"
    }).json()
    token2 = s2["access_token"]

    q = client.post("/api/admin/questions", json={
        "question_text": "What hill did Lord Krishna lift on His little finger?",
        "option_a": "Govardhana",
        "option_b": "Kailash",
        "option_c": "Mandara",
        "option_d": "Gandhamadana",
        "correct_option": "A",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # Open WebSocket for Student 1 and Student 2
    with client.websocket_connect(f"/api/ws/quiz?token={token1}") as ws1:
        # Read initial state for s1
        init1 = ws1.receive_json()
        assert init1["type"] == "quiz_state"

        with client.websocket_connect(f"/api/ws/quiz?token={token2}") as ws2:
            # Read initial state for s2
            init2 = ws2.receive_json()
            assert init2["type"] == "quiz_state"

            # Admin starts round via HTTP endpoint
            round_res = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers)
            assert round_res.status_code == 201
            r_id = round_res.json()["id"]

            # Both students should receive 'question_started'
            event1 = ws1.receive_json()
            assert event1["type"] == "question_started"
            assert event1["data"]["round_id"] == r_id
            assert event1["data"]["question"]["question_text"] == "What hill did Lord Krishna lift on His little finger?"
            assert "correct_option" not in event1["data"]["question"]

            event2 = ws2.receive_json()
            assert event2["type"] == "question_started"
            assert event2["data"]["round_id"] == r_id
            assert "correct_option" not in event2["data"]["question"]

            # Admin ends round via HTTP endpoint
            end_res = client.post(f"/api/admin/rounds/{r_id}/end", headers=admin_auth_headers)
            assert end_res.status_code == 200

            # Both students should receive 'round_ended'
            end_event1 = ws1.receive_json()
            assert end_event1["type"] == "round_ended"
            assert end_event1["data"]["round_id"] == r_id

            end_event2 = ws2.receive_json()
            assert end_event2["type"] == "round_ended"
            assert end_event2["data"]["round_id"] == r_id


def test_multiple_connections_per_student(client: TestClient, admin_auth_headers: dict):
    """8. A student opening multiple tabs gets broadcasts on both tabs."""
    s = client.post("/api/students/register", json={
        "name": "WS Multi Tab",
        "registration_number": "WSMT001",
        "branch": "CSE",
        "phone": "+919876541005",
        "email": "wsmt@college.edu"
    }).json()
    token = s["access_token"]

    q = client.post("/api/admin/questions", json={
        "question_text": "Multi-tab test question?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "B",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # Open Tab 1
    with client.websocket_connect(f"/api/ws/quiz?token={token}") as tab1:
        tab1.receive_json()  # discard initial state

        # Open Tab 2
        with client.websocket_connect(f"/api/ws/quiz?token={token}") as tab2:
            tab2.receive_json()  # discard initial state

            # Admin starts round
            r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

            # Both tabs receive event
            ev1 = tab1.receive_json()
            ev2 = tab2.receive_json()
            assert ev1["type"] == "question_started"
            assert ev2["type"] == "question_started"
            assert ev1["data"]["round_id"] == r["id"]
            assert ev2["data"]["round_id"] == r["id"]


def test_disconnect_one_student_does_not_affect_other(client: TestClient, admin_auth_headers: dict):
    """9. Disconnecting one student leaves the other connected and functioning."""
    s1 = client.post("/api/students/register", json={
        "name": "WS Disc 1",
        "registration_number": "WSD001",
        "branch": "CSE",
        "phone": "+919876541006",
        "email": "wsd1@college.edu"
    }).json()
    token1 = s1["access_token"]

    s2 = client.post("/api/students/register", json={
        "name": "WS Stay 2",
        "registration_number": "WSD002",
        "branch": "IT",
        "phone": "+919876541007",
        "email": "wsd2@college.edu"
    }).json()
    token2 = s2["access_token"]

    q = client.post("/api/admin/questions", json={
        "question_text": "Disconnect resilience test question?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "C",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    # Open s2 socket
    with client.websocket_connect(f"/api/ws/quiz?token={token2}") as ws2:
        ws2.receive_json()  # initial state

        # Connect and immediately disconnect s1
        with client.websocket_connect(f"/api/ws/quiz?token={token1}") as ws1:
            ws1.receive_json()
        # ws1 is now closed!

        # Admin starts round
        r = client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers).json()

        # ws2 receives broadcast without issue
        ev2 = ws2.receive_json()
        assert ev2["type"] == "question_started"
        assert ev2["data"]["round_id"] == r["id"]


def test_ping_pong_keepalive(client: TestClient):
    """10. Test ping keepalive returns pong."""
    s = client.post("/api/students/register", json={
        "name": "WS Ping",
        "registration_number": "WSP001",
        "branch": "CSE",
        "phone": "+919876541008",
        "email": "wsp@college.edu"
    }).json()
    token = s["access_token"]

    with client.websocket_connect(f"/api/ws/quiz?token={token}") as ws:
        ws.receive_json()  # initial state
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp["type"] == "pong"


def test_resilient_broadcast_handles_faulty_socket():
    """11. Verify ConnectionManager prunes failed sockets without breaking broadcast to healthy sockets."""
    async def run():
        mgr = connection_manager

        # Mock working socket
        good_socket = AsyncMock()
        # Mock failing socket
        bad_socket = AsyncMock()
        bad_socket.send_text.side_effect = RuntimeError("Socket write failed")

        # Manually register sockets under student IDs
        async with mgr._lock:
            mgr._connections[100] = {good_socket}
            mgr._connections[101] = {bad_socket}

        event = QuestionStartedEvent(
            data=QuestionStartedData(
                round_id=99,
                question=PublicQuestionResponse(
                    id=1,
                    question_text="Resilience test question",
                    option_a="A",
                    option_b="B",
                    option_c="C",
                    option_d="D"
                ),
                started_at=datetime.now(timezone.utc)
            )
        )

        # Broadcast event
        await mgr.broadcast(event)

        # Good socket received message
        assert good_socket.send_text.called
        # Bad socket was invoked and pruned
        assert bad_socket.send_text.called
        assert 101 not in mgr._connections

        # Cleanup
        async with mgr._lock:
            mgr._connections.clear()

    asyncio.run(run())


def test_websocket_never_exposes_secrets(client: TestClient, admin_auth_headers: dict):
    """12. Verify WS event messages never contain secret keys or password hashes."""
    s = client.post("/api/students/register", json={
        "name": "WS Secret Test",
        "registration_number": "WSS001",
        "branch": "CSE",
        "phone": "+919876541009",
        "email": "wss@college.edu"
    }).json()
    token = s["access_token"]

    q = client.post("/api/admin/questions", json={
        "question_text": "Secret check question?",
        "option_a": "A",
        "option_b": "B",
        "option_c": "C",
        "option_d": "D",
        "correct_option": "D",
        "is_active": True,
    }, headers=admin_auth_headers).json()

    with client.websocket_connect(f"/api/ws/quiz?token={token}") as ws:
        init_text = ws.receive_text()
        assert settings.JWT_SECRET_KEY not in init_text
        assert settings.STUDENT_JWT_SECRET_KEY not in init_text
        assert settings.ADMIN_PASSWORD_HASH not in init_text
        assert "correct_option" not in init_text

        # Admin starts round
        client.post("/api/admin/rounds/start", json={"question_id": q["id"]}, headers=admin_auth_headers)

        q_start_text = ws.receive_text()
        assert settings.JWT_SECRET_KEY not in q_start_text
        assert settings.STUDENT_JWT_SECRET_KEY not in q_start_text
        assert settings.ADMIN_PASSWORD_HASH not in q_start_text
        assert "correct_option" not in q_start_text
