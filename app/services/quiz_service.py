from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session, select
from app.models.enums import RoundStatus, OptionEnum
from app.models.quiz_round import QuizRound
from app.models.student import Student
from app.models.question import Question
from app.models.answer import Answer
from app.schemas.question import PublicQuestionResponse
from app.schemas.quiz import ActiveQuizStateResponse, RoundEndResponse, QuizRoundResponse
from app.schemas.answer import AnswerResponse
from app.crud import quiz as quiz_crud
from app.crud import questions as question_crud
from app.crud import students as student_crud
from app.crud import answers as answer_crud
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    RoundNotActiveException,
)


def get_active_quiz_state(session: Session) -> ActiveQuizStateResponse:
    """Retrieve the current live quiz state and active question for students."""
    now = datetime.now(timezone.utc)
    active_round = quiz_crud.get_active_round(session)

    if not active_round:
        return ActiveQuizStateResponse(
            is_active=False,
            round_id=None,
            status=RoundStatus.PENDING,
            started_at=None,
            server_time=now,
            question=None,
        )

    # Load associated question
    question = question_crud.get_question_by_id(session, active_round.question_id)
    public_q = None
    if question:
        public_q = PublicQuestionResponse(
            id=question.id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
        )

    return ActiveQuizStateResponse(
        is_active=True,
        round_id=active_round.id,
        status=active_round.status,
        started_at=active_round.started_at,
        server_time=now,
        question=public_q,
    )


def submit_student_answer(
    session: Session,
    round_id: int,
    student_id: int,
    selected_option: OptionEnum
) -> AnswerResponse:
    """
    Process a student's answer submission:
    - Verifies round is active.
    - Computes server-authoritative response time.
    - Evaluates correctness.
    - Enforces single submission per round via database constraint.
    """
    # 1. Verify round
    db_round = quiz_crud.get_round_by_id(session, round_id)
    if not db_round:
        raise NotFoundException(f"Quiz round with ID {round_id} does not exist.")

    if db_round.status != RoundStatus.ACTIVE or db_round.started_at is None:
        if db_round.status == RoundStatus.ENDED:
            raise BadRequestException("This quiz round has already ended.", error_code="ROUND_ENDED")
        raise RoundNotActiveException("This quiz round is not currently active.")

    # 2. Verify student
    db_student = student_crud.get_student_by_id(session, student_id)
    if not db_student:
        raise NotFoundException(f"Student with ID {student_id} not found.", error_code="STUDENT_NOT_FOUND")

    # 3. Verify question
    db_question = question_crud.get_question_by_id(session, db_round.question_id)
    if not db_question:
        raise NotFoundException("Associated question not found.", error_code="QUESTION_NOT_FOUND")

    # 4. Server-authoritative timing calculation
    answered_at = datetime.now(timezone.utc)
    
    # Ensure started_at is timezone-aware UTC for accurate delta calculation
    round_start = db_round.started_at
    if round_start.tzinfo is None:
        round_start = round_start.replace(tzinfo=timezone.utc)
    
    time_delta = answered_at - round_start
    response_time_ms = max(0, int(time_delta.total_seconds() * 1000))

    # 5. Evaluate correctness on server
    is_correct = (selected_option == db_question.correct_option)

    # 6. Save answer
    db_answer = answer_crud.record_answer(
        session=session,
        round_id=db_round.id,
        student_id=db_student.id,
        selected_option=selected_option,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
        answered_at=answered_at,
    )

    return AnswerResponse.model_validate(db_answer)


def start_quiz_round(session: Session, question_id: int) -> QuizRoundResponse:
    """Admin starts a new quiz round for a question."""
    question = question_crud.get_question_by_id(session, question_id)
    if not question:
        raise NotFoundException(f"Question with ID {question_id} not found.")

    if not question.is_active:
        raise BadRequestException("Cannot start round with an inactive question.")

    new_round = quiz_crud.start_new_round(session, question_id)
    return QuizRoundResponse.model_validate(new_round)


def end_quiz_round(session: Session, round_id: int) -> RoundEndResponse:
    """Admin ends an active quiz round."""
    ended_round = quiz_crud.end_round(session, round_id)
    answers = answer_crud.get_answers_for_round(session, round_id)
    total_correct = sum(1 for a in answers if a.is_correct)

    return RoundEndResponse(
        round_id=ended_round.id,
        status=ended_round.status,
        started_at=ended_round.started_at,
        ended_at=ended_round.ended_at,
        total_answers=len(answers),
        total_correct=total_correct,
    )
