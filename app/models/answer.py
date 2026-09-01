from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel, Relationship
from app.models.enums import OptionEnum

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.quiz_round import QuizRound


class Answer(SQLModel, table=True):
    __tablename__ = "answer"
    __table_args__ = (
        UniqueConstraint("round_id", "student_id", name="uq_round_student"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    round_id: int = Field(foreign_key="quizround.id", index=True, nullable=False)
    student_id: int = Field(foreign_key="student.id", index=True, nullable=False)
    selected_option: OptionEnum = Field(nullable=False)
    is_correct: bool = Field(index=True, nullable=False)
    response_time_ms: int = Field(index=True, nullable=False)
    answered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    student: Optional["Student"] = Relationship(back_populates="answers")
    round: Optional["QuizRound"] = Relationship(back_populates="answers")
