from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the student")
    registration_number: str = Field(..., min_length=1, max_length=50, description="College registration / roll number")
    branch: str = Field(..., min_length=1, max_length=50, description="Academic branch / department")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone number")
    email: EmailStr = Field(..., description="Student email address (e.g. Gmail)")

    @field_validator("name", "registration_number", "branch", "phone", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty or blank")
        return v


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    branch: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None


class StudentResponse(StudentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentAuthResponse(BaseModel):
    """Response returned upon student registration, containing profile and access token."""
    student: StudentResponse
    access_token: str = Field(..., description="Student JWT access token for quiz authentication")
    token_type: str = Field("bearer", description="Token authorization scheme")
