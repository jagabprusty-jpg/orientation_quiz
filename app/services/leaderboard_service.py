from typing import List, Tuple
from sqlmodel import Session, select
from app.models.quiz_round import QuizRound
from app.models.answer import Answer
from app.models.student import Student
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.crud import quiz as quiz_crud
from app.core.exceptions import NotFoundException


def get_round_leaderboard(session: Session, round_id: int) -> LeaderboardResponse:
    """
    Compute leaderboard for a single independent quiz round:
    - Only correct answers are ranked (1..N).
    - Ranked by response_time_ms ascending.
    - Top 5 correct fastest participants are marked with is_top_5 = True.
    - Incorrect answers are listed without prize rank or prize flag.
    - No cumulative score is carried between rounds.
    """
    db_round = quiz_crud.get_round_by_id(session, round_id)
    if not db_round:
        raise NotFoundException(f"Quiz round with ID {round_id} not found.")

    # Fetch answers with associated student details
    statement = (
        select(Answer, Student)
        .join(Student, Answer.student_id == Student.id)
        .where(Answer.round_id == round_id)
        .order_by(Answer.response_time_ms.asc(), Answer.answered_at.asc())
    )
    results = session.exec(statement).all()

    correct_pairs: List[Tuple[Answer, Student]] = []
    incorrect_pairs: List[Tuple[Answer, Student]] = []

    for answer, student in results:
        if answer.is_correct:
            correct_pairs.append((answer, student))
        else:
            incorrect_pairs.append((answer, student))

    # Rank correct answers
    ranked_correct_entries: List[LeaderboardEntry] = []
    for rank_idx, (answer, student) in enumerate(correct_pairs, start=1):
        is_top_5 = rank_idx <= 5
        entry = LeaderboardEntry(
            rank=rank_idx,
            is_top_5=is_top_5,
            student_id=student.id,
            student_name=student.name,
            registration_number=student.registration_number,
            branch=student.branch,
            selected_option=answer.selected_option,
            is_correct=True,
            response_time_ms=answer.response_time_ms,
            answered_at=answer.answered_at,
        )
        ranked_correct_entries.append(entry)

    # Top 5 winners
    top_5_winners = ranked_correct_entries[:5]

    # Incorrect entries (unranked, never eligible for Top 5)
    incorrect_entries: List[LeaderboardEntry] = []
    for answer, student in incorrect_pairs:
        entry = LeaderboardEntry(
            rank=None,
            is_top_5=False,
            student_id=student.id,
            student_name=student.name,
            registration_number=student.registration_number,
            branch=student.branch,
            selected_option=answer.selected_option,
            is_correct=False,
            response_time_ms=answer.response_time_ms,
            answered_at=answer.answered_at,
        )
        incorrect_entries.append(entry)

    # Combined list: all correct ranked first, then incorrect
    all_entries = ranked_correct_entries + incorrect_entries

    return LeaderboardResponse(
        round_id=db_round.id,
        question_id=db_round.question_id,
        round_status=db_round.status,
        started_at=db_round.started_at,
        ended_at=db_round.ended_at,
        total_submissions=len(results),
        total_correct=len(correct_pairs),
        total_incorrect=len(incorrect_pairs),
        top_5_winners=top_5_winners,
        ranked_correct_entries=ranked_correct_entries,
        all_entries=all_entries,
    )


def get_current_leaderboard(session: Session) -> LeaderboardResponse:
    """Retrieve leaderboard for the active round or most recent round."""
    active_round = quiz_crud.get_active_round(session)
    if active_round:
        return get_round_leaderboard(session, active_round.id)

    latest_round = quiz_crud.get_latest_round(session)
    if latest_round:
        return get_round_leaderboard(session, latest_round.id)

    raise NotFoundException("No quiz rounds have been started yet.", error_code="NO_ROUNDS")
