import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import decode_student_access_token
from app.core.exceptions import UnauthorizedException
from app.crud import students as student_crud
from app.services import quiz_service
from app.realtime.connection_manager import connection_manager
from app.realtime.events import QuizStateData, QuizStateEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Realtime WebSockets"])


@router.websocket("/ws/quiz")
async def quiz_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Student JWT access token"),
    session: Session = Depends(get_session)
):
    """
    Live WebSocket connection endpoint for students:
    - Path: WS /api/ws/quiz?token=<student_access_token>
    - Authenticates student using server-signed JWT token.
    - Rejects missing, invalid, or expired tokens with WebSocket close code 1008 (Policy Violation).
    - On connection/reconnection, immediately sends the current quiz state (active question or waiting).
    - Keeps connection open to receive broadcast events (question_started, round_ended, etc.).
    """
    if not token:
        logger.warning("WebSocket connection rejected: token query parameter missing.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token query parameter required")
        return

    # Validate student token
    try:
        student_id = decode_student_access_token(token)
    except UnauthorizedException as exc:
        logger.warning(f"WebSocket token validation failed: {exc.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # Validate student exists in database
    student = student_crud.get_student_by_id(session, student_id)
    if not student:
        logger.warning(f"WebSocket connection rejected: student ID {student_id} not in database.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Student not registered")
        return

    # Accept connection and register with connection manager
    await connection_manager.connect(student_id, websocket)

    try:
        # Immediately fetch and send current quiz state on connect / reconnect
        active_state = quiz_service.get_active_quiz_state(session)
        if active_state.is_active and active_state.question:
            state_data = QuizStateData(
                status="active",
                round_id=active_state.round_id,
                question=active_state.question,
                started_at=active_state.started_at,
                server_time=active_state.server_time,
            )
        else:
            state_data = QuizStateData(
                status="waiting",
                round_id=None,
                question=None,
                started_at=None,
                server_time=datetime.now(timezone.utc),
            )

        state_event = QuizStateEvent(data=state_data)
        await websocket.send_text(state_event.model_dump_json())

        # Receive loop for client keepalives / messages
        while True:
            client_msg = await websocket.receive_text()
            if client_msg.strip().lower() == "ping":
                await websocket.send_text('{"type":"pong"}')

    except WebSocketDisconnect:
        logger.info(f"Student {student_id} disconnected normally.")
    except Exception as exc:
        logger.warning(f"WebSocket error for student {student_id}: {exc}")
    finally:
        await connection_manager.disconnect(student_id, websocket)
