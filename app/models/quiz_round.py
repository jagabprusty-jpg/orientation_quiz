from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, SQLModel, Relationship
from app.models.enums import RoundStatus

if TYPE_CHECKING:
    from app.models.question import Question
    from app.models.answer import Answer


class QuizRound(SQLModel, table=True):
    __tablename__ = "quizround"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id", index=True, nullable=False)
    status: RoundStatus = Field(
        default=RoundStatus.PENDING,
        index=True,
        nullable=False
    )
    started_at: Optional[datetime] = Field(default=None, nullable=True)
    ended_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    question: Optional["Question"] = Relationship(back_populates="rounds")
    answers: List["Answer"] = Relationship(back_populates="round")
