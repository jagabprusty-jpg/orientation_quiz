from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import OptionEnum, RoundStatus


class LeaderboardEntry(BaseModel):
    rank: Optional[int] = None  # 1..N for correct answers, None for incorrect
    is_top_5: bool = False      # Highlighted prize position
    student_id: int
    student_name: str
    registration_number: str
    branch: str
    selected_option: OptionEnum
    is_correct: bool
    response_time_ms: int
    answered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    round_id: int
    question_id: int
    round_status: RoundStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_submissions: int
    total_correct: int
    total_incorrect: int
    top_5_winners: List[LeaderboardEntry]
    ranked_correct_entries: List[LeaderboardEntry]
    all_entries: List[LeaderboardEntry]

    model_config = ConfigDict(from_attributes=True)
