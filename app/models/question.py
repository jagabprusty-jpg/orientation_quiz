from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, SQLModel, Relationship
from app.models.enums import OptionEnum

if TYPE_CHECKING:
    from app.models.quiz_round import QuizRound


class Question(SQLModel, table=True):
    __tablename__ = "question"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_text: str = Field(nullable=False)
    option_a: str = Field(nullable=False)
    option_b: str = Field(nullable=False)
    option_c: str = Field(nullable=False)
    option_d: str = Field(nullable=False)
    correct_option: OptionEnum = Field(nullable=False)
    is_active: bool = Field(default=True, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    rounds: List["QuizRound"] = Relationship(back_populates="question")
