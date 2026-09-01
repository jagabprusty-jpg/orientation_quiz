from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.answer import Answer


class Student(SQLModel, table=True):
    __tablename__ = "student"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    registration_number: str = Field(unique=True, index=True, nullable=False)
    branch: str = Field(nullable=False)
    phone: str = Field(index=True, nullable=False)
    email: str = Field(unique=True, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    answers: List["Answer"] = Relationship(back_populates="student")
