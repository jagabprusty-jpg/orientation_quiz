from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select
from app.models.quiz_round import QuizRound
from app.models.enums import RoundStatus
from app.core.exceptions import NotFoundException, BadRequestException


def get_round_by_id(session: Session, round_id: int) -> Optional[QuizRound]:
    """Retrieve round by primary key ID."""
    return session.get(QuizRound, round_id)


def get_active_round(session: Session) -> Optional[QuizRound]:
    """Retrieve the currently active round, if any."""
    statement = (
        select(QuizRound)
        .where(QuizRound.status == RoundStatus.ACTIVE)
        .order_by(QuizRound.started_at.desc())
    )
    return session.exec(statement).first()


def get_latest_round(session: Session) -> Optional[QuizRound]:
    """Retrieve the latest round (active or ended)."""
    statement = select(QuizRound).order_by(QuizRound.id.desc())
    return session.exec(statement).first()


def get_all_rounds(session: Session, skip: int = 0, limit: int = 100) -> List[QuizRound]:
    """Retrieve paginated list of quiz rounds."""
    statement = select(QuizRound).order_by(QuizRound.id.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def start_new_round(session: Session, question_id: int) -> QuizRound:
    """
    Start a new round for a question:
    1. Ends any currently active rounds.
    2. Creates and activates the new round with precise UTC start time.
    """
    now = datetime.now(timezone.utc)

    # Automatically end any active rounds
    active_rounds = session.exec(
        select(QuizRound).where(QuizRound.status == RoundStatus.ACTIVE)
    ).all()
    for active_round in active_rounds:
        active_round.status = RoundStatus.ENDED
        active_round.ended_at = now
        session.add(active_round)

    # Create new active round
    new_round = QuizRound(
        question_id=question_id,
        status=RoundStatus.ACTIVE,
        started_at=now,
        ended_at=None,
    )
    session.add(new_round)
    session.commit()
    session.refresh(new_round)
    return new_round


def end_round(session: Session, round_id: int) -> QuizRound:
    """End an active quiz round."""
    db_round = get_round_by_id(session, round_id)
    if not db_round:
        raise NotFoundException(f"Quiz round with ID {round_id} not found.")

    if db_round.status == RoundStatus.ENDED:
        return db_round

    db_round.status = RoundStatus.ENDED
    db_round.ended_at = datetime.now(timezone.utc)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round
