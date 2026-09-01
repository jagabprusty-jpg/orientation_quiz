from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.enums import OptionEnum


class QuestionBase(BaseModel):
    question_text: str = Field(..., min_length=1, description="Text of the question")
    option_a: str = Field(..., min_length=1, description="Option A")
    option_b: str = Field(..., min_length=1, description="Option B")
    option_c: str = Field(..., min_length=1, description="Option C")
    option_d: str = Field(..., min_length=1, description="Option D")

    @field_validator("question_text", "option_a", "option_b", "option_c", "option_d", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty or blank")
        return v


class QuestionCreate(QuestionBase):
    correct_option: OptionEnum = Field(..., description="The correct option (A, B, C, or D)")
    is_active: bool = Field(default=True, description="Whether the question is available for rounds")


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_option: Optional[OptionEnum] = None
    is_active: Optional[bool] = None


class QuestionResponse(QuestionBase):
    """Full question details for Admin."""
    id: int
    correct_option: OptionEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicQuestionResponse(QuestionBase):
    """Public question details for Students. NEVER exposes correct_option."""
    id: int

    model_config = ConfigDict(from_attributes=True)
