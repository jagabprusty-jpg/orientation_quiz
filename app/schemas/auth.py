from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Admin username")
    password: str = Field(..., min_length=1, description="Admin plaintext password")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Username cannot be blank")
        return v


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer token")
    token_type: str = Field("bearer", description="Token type")


class AdminResponse(BaseModel):
    username: str = Field(..., description="Authenticated admin username")
    role: str = Field("admin", description="Admin role")
