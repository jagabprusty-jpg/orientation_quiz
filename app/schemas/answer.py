from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import OptionEnum


class AnswerSubmit(BaseModel):
    """
    Payload submitted by the authenticated student for a quiz round.
    Student identity is derived strictly from the authentication token.
    Extra fields (e.g. student_id, is_correct, response_time_ms) are strictly forbidden.
    """
    selected_option: OptionEnum = Field(..., description="The chosen option: A, B, C, or D")

    model_config = ConfigDict(extra="forbid")


class AnswerResponse(BaseModel):
    """Result of answer submission."""
    id: int
    round_id: int
    student_id: int
    selected_option: OptionEnum
    is_correct: bool
    response_time_ms: int
    answered_at: datetime

    model_config = ConfigDict(from_attributes=True)
