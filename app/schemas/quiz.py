from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import RoundStatus
from app.schemas.question import PublicQuestionResponse


class QuizRoundCreate(BaseModel):
    question_id: int = Field(..., description="ID of the question to start a round for")


class QuizRoundResponse(BaseModel):
    id: int
    question_id: int
    status: RoundStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveQuizStateResponse(BaseModel):
    """Response returned to students querying the current live quiz state."""
    is_active: bool
    round_id: Optional[int] = None
    status: RoundStatus
    started_at: Optional[datetime] = None
    server_time: datetime
    question: Optional[PublicQuestionResponse] = None


class RoundEndResponse(BaseModel):
    round_id: int
    status: RoundStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_answers: int
    total_correct: int
