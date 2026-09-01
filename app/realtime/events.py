from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from app.schemas.question import PublicQuestionResponse
from app.schemas.leaderboard import LeaderboardResponse


class BaseEvent(BaseModel):
    """Base model for all real-time WebSocket events."""
    type: str
    data: Any


# 1. Initial / Reconnect State Event
class QuizStateData(BaseModel):
    status: str = Field(..., description="Current state: 'active', 'waiting', or 'ended'")
    round_id: Optional[int] = Field(None, description="Active round ID if active")
    question: Optional[PublicQuestionResponse] = Field(
        None,
        description="Public question payload (strictly excludes correct_option)"
    )
    started_at: Optional[datetime] = Field(None, description="UTC timestamp when round started")
    server_time: datetime = Field(..., description="Current UTC server time")


class QuizStateEvent(BaseEvent):
    type: str = "quiz_state"
    data: QuizStateData


# 2. Question Started Event (Admin starts a new round)
class QuestionStartedData(BaseModel):
    round_id: int = Field(..., description="Newly started round ID")
    question: PublicQuestionResponse = Field(
        ...,
        description="Public question payload (strictly excludes correct_option)"
    )
    started_at: datetime = Field(..., description="UTC timestamp when round started")


class QuestionStartedEvent(BaseEvent):
    type: str = "question_started"
    data: QuestionStartedData


# 3. Round Ended Event (Admin ends current round)
class RoundEndedData(BaseModel):
    round_id: int = Field(..., description="Ended round ID")
    ended_at: datetime = Field(..., description="UTC timestamp when round ended")


class RoundEndedEvent(BaseEvent):
    type: str = "round_ended"
    data: RoundEndedData


# 4. Optional Leaderboard Broadcast Event
class LeaderboardUpdatedEvent(BaseEvent):
    type: str = "leaderboard_updated"
    data: LeaderboardResponse
