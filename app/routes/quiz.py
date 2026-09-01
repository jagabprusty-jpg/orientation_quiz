from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.security import get_current_student
from app.schemas.quiz import ActiveQuizStateResponse
from app.schemas.answer import AnswerSubmit, AnswerResponse
from app.schemas.leaderboard import LeaderboardResponse
from app.models.student import Student
from app.services import quiz_service, leaderboard_service
from app.crud import quiz as quiz_crud
from app.core.exceptions import RoundNotActiveException

router = APIRouter(prefix="/quiz", tags=["Live Quiz"])


@router.get(
    "/active",
    response_model=ActiveQuizStateResponse,
    summary="Get currently active quiz round and question (Public)"
)
def get_active_quiz(session: Session = Depends(get_session)):
    """
    Returns the live active question for students.
    NEVER exposes the correct option.
    """
    return quiz_service.get_active_quiz_state(session)


@router.post(
    "/rounds/{round_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit answer for a specific quiz round (Authenticated Student)"
)
def submit_answer_for_round(
    round_id: int,
    answer_in: AnswerSubmit,
    current_student: Student = Depends(get_current_student),
    session: Session = Depends(get_session)
):
    """
    Submit an answer for an active round:
    - Student identity is securely derived from the authenticated token (current_student.id).
    - Calculates server-authoritative response time (answered_at - round.started_at).
    - Evaluates correctness against stored question.
    - Rejects duplicate answers for the same round (HTTP 409 Conflict).
    - Rejects answers if the round is not active or has ended (HTTP 400 Bad Request).
    """
    return quiz_service.submit_student_answer(
        session=session,
        round_id=round_id,
        student_id=current_student.id,
        selected_option=answer_in.selected_option,
    )


@router.post(
    "/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit answer for the currently active quiz round (Authenticated Student)"
)
def submit_answer_for_active_round(
    answer_in: AnswerSubmit,
    current_student: Student = Depends(get_current_student),
    session: Session = Depends(get_session)
):
    """
    Convenience endpoint to submit answer for the current active round:
    - Student identity derived solely from authenticated token.
    """
    active_round = quiz_crud.get_active_round(session)
    if not active_round:
        raise RoundNotActiveException("There is no active round at this moment.")

    return quiz_service.submit_student_answer(
        session=session,
        round_id=active_round.id,
        student_id=current_student.id,
        selected_option=answer_in.selected_option,
    )


@router.get(
    "/rounds/{round_id}/leaderboard",
    response_model=LeaderboardResponse,
    summary="Get leaderboard for a specific quiz round (Public)"
)
def get_round_leaderboard(
    round_id: int,
    session: Session = Depends(get_session)
):
    """
    Returns leaderboard for a specific round:
    - Top 5 fastest correct students are highlighted (`is_top_5 = True`).
    - Incorrect answers are not eligible for prize rankings.
    - Personal contact info (phone/email) is NEVER exposed.
    """
    return leaderboard_service.get_round_leaderboard(session, round_id)


@router.get(
    "/leaderboard/current",
    response_model=LeaderboardResponse,
    summary="Get leaderboard for the current/latest quiz round (Public)"
)
def get_current_leaderboard(session: Session = Depends(get_session)):
    """Returns leaderboard for the currently active or latest ended round."""
    return leaderboard_service.get_current_leaderboard(session)
