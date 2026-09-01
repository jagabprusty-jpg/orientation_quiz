from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlmodel import Session
from app.core.database import get_session
from app.core.security import get_current_admin
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse, PublicQuestionResponse
from app.schemas.quiz import QuizRoundCreate, QuizRoundResponse, RoundEndResponse
from app.schemas.leaderboard import LeaderboardResponse
from app.crud import questions as question_crud
from app.crud import quiz as quiz_crud
from app.services import quiz_service, leaderboard_service
from app.core.exceptions import NotFoundException
from app.realtime.connection_manager import connection_manager
from app.realtime.events import (
    QuestionStartedData,
    QuestionStartedEvent,
    RoundEndedData,
    RoundEndedEvent,
)

# Protect ALL admin endpoints with get_current_admin dependency
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)]
)


# ==========================================
# Question Management Endpoints
# ==========================================

@router.post(
    "/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quiz question (Admin)"
)
def create_question(
    question_in: QuestionCreate,
    session: Session = Depends(get_session)
):
    return question_crud.create_question(session, question_in)


@router.get(
    "/questions",
    response_model=List[QuestionResponse],
    summary="List all questions (Admin)"
)
def list_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(False),
    session: Session = Depends(get_session)
):
    return question_crud.get_all_questions(session, skip=skip, limit=limit, active_only=active_only)


@router.get(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Get question details including correct answer (Admin)"
)
def get_question(
    question_id: int,
    session: Session = Depends(get_session)
):
    question = question_crud.get_question_by_id(session, question_id)
    if not question:
        raise NotFoundException(f"Question with ID {question_id} not found.")
    return question


@router.put(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Update question details (Admin)"
)
def update_question(
    question_id: int,
    question_in: QuestionUpdate,
    session: Session = Depends(get_session)
):
    return question_crud.update_question(session, question_id, question_in)


@router.delete(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Deactivate question (Admin)"
)
def delete_question(
    question_id: int,
    session: Session = Depends(get_session)
):
    return question_crud.deactivate_or_delete_question(session, question_id)


# ==========================================
# Quiz Round Management Endpoints
# ==========================================

@router.post(
    "/rounds/start",
    response_model=QuizRoundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new quiz round for a question (Admin)"
)
async def start_round(
    round_in: QuizRoundCreate,
    session: Session = Depends(get_session)
):
    """
    Start a live round for a question:
    1. Ends any existing active round.
    2. Sets precise server start timestamp.
    3. Commits transaction to database.
    4. Broadcasts question_started event to all connected students.
    """
    new_round = quiz_service.start_quiz_round(session, round_in.question_id)
    question = question_crud.get_question_by_id(session, round_in.question_id)

    if question:
        public_q = PublicQuestionResponse(
            id=question.id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
        )
        event = QuestionStartedEvent(
            data=QuestionStartedData(
                round_id=new_round.id,
                question=public_q,
                started_at=new_round.started_at,
            )
        )
        await connection_manager.broadcast(event)

    return new_round


@router.post(
    "/rounds/{round_id}/end",
    response_model=RoundEndResponse,
    summary="End an active quiz round (Admin)"
)
async def end_round(
    round_id: int,
    session: Session = Depends(get_session)
):
    """
    End the specified quiz round:
    1. Ends round in database and commits.
    2. Broadcasts round_ended event to all connected students.
    """
    round_summary = quiz_service.end_quiz_round(session, round_id)

    event = RoundEndedEvent(
        data=RoundEndedData(
            round_id=round_summary.round_id,
            ended_at=round_summary.ended_at,
        )
    )
    await connection_manager.broadcast(event)

    return round_summary


@router.get(
    "/rounds",
    response_model=List[QuizRoundResponse],
    summary="List all quiz rounds (Admin)"
)
def list_rounds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session)
):
    return quiz_crud.get_all_rounds(session, skip=skip, limit=limit)


@router.get(
    "/rounds/{round_id}",
    response_model=QuizRoundResponse,
    summary="Get details of a specific round (Admin)"
)
def get_round(
    round_id: int,
    session: Session = Depends(get_session)
):
    db_round = quiz_crud.get_round_by_id(session, round_id)
    if not db_round:
        raise NotFoundException(f"Quiz round with ID {round_id} not found.")
    return db_round


@router.get(
    "/rounds/{round_id}/leaderboard",
    response_model=LeaderboardResponse,
    summary="View leaderboard for a round (Admin)"
)
def get_admin_round_leaderboard(
    round_id: int,
    session: Session = Depends(get_session)
):
    return leaderboard_service.get_round_leaderboard(session, round_id)
