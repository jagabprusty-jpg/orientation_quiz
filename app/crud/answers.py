from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.models.answer import Answer
from app.models.enums import OptionEnum
from app.core.exceptions import DuplicateAnswerException


def get_answer_by_id(session: Session, answer_id: int) -> Optional[Answer]:
    """Retrieve answer by ID."""
    return session.get(Answer, answer_id)


def get_answer_by_round_and_student(
    session: Session,
    round_id: int,
    student_id: int
) -> Optional[Answer]:
    """Check if student has already answered this round."""
    statement = select(Answer).where(
        Answer.round_id == round_id,
        Answer.student_id == student_id
    )
    return session.exec(statement).first()


def get_answers_for_round(session: Session, round_id: int) -> List[Answer]:
    """Retrieve all answers submitted for a round."""
    statement = (
        select(Answer)
        .where(Answer.round_id == round_id)
        .order_by(Answer.response_time_ms.asc(), Answer.answered_at.asc())
    )
    return list(session.exec(statement).all())


def record_answer(
    session: Session,
    round_id: int,
    student_id: int,
    selected_option: OptionEnum,
    is_correct: bool,
    response_time_ms: int,
    answered_at: datetime
) -> Answer:
    """
    Record an answer with database-level uniqueness enforcement on (round_id, student_id).
    """
    # Pre-check at application level
    existing = get_answer_by_round_and_student(session, round_id, student_id)
    if existing:
        raise DuplicateAnswerException()

    db_answer = Answer(
        round_id=round_id,
        student_id=student_id,
        selected_option=selected_option,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
        answered_at=answered_at,
    )

    try:
        session.add(db_answer)
        session.commit()
        session.refresh(db_answer)
        return db_answer
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateAnswerException() from exc
