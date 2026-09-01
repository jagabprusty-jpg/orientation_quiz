from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.core.exceptions import NotFoundException


def get_question_by_id(session: Session, question_id: int) -> Optional[Question]:
    """Retrieve question by ID."""
    return session.get(Question, question_id)


def get_all_questions(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False
) -> List[Question]:
    """Retrieve paginated questions."""
    statement = select(Question)
    if active_only:
        statement = statement.where(Question.is_active.is_(True))
    statement = statement.offset(skip).limit(limit)
    return list(session.exec(statement).all())


def create_question(session: Session, question_in: QuestionCreate) -> Question:
    """Create a new quiz question."""
    db_question = Question(
        question_text=question_in.question_text,
        option_a=question_in.option_a,
        option_b=question_in.option_b,
        option_c=question_in.option_c,
        option_d=question_in.option_d,
        correct_option=question_in.correct_option,
        is_active=question_in.is_active,
    )
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question


def update_question(
    session: Session,
    question_id: int,
    question_in: QuestionUpdate
) -> Question:
    """Update question fields."""
    db_question = get_question_by_id(session, question_id)
    if not db_question:
        raise NotFoundException(f"Question with ID {question_id} not found.")

    update_data = question_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_question, field, value)

    db_question.updated_at = datetime.now(timezone.utc)
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question


def deactivate_or_delete_question(session: Session, question_id: int) -> Question:
    """Deactivate question so it cannot be used for new rounds."""
    db_question = get_question_by_id(session, question_id)
    if not db_question:
        raise NotFoundException(f"Question with ID {question_id} not found.")

    db_question.is_active = False
    db_question.updated_at = datetime.now(timezone.utc)
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question
