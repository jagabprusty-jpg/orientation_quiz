from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Live Janmashtami College Quiz API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./quiz.db"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Admin Authentication & Security
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$6Kdt6v6y1FlBppJu49zTzuOpViT2jBLMzVbvRSgQ4GDKZobIlXPee"
    JWT_SECRET_KEY: str = "super-secret-janmashtami-quiz-key-change-in-production-min-32-chars-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # Student Authentication & Security (Separate secret and lifetime)
    STUDENT_JWT_SECRET_KEY: str = "super-secret-student-quiz-key-change-in-production-min-32-chars-long"
    STUDENT_JWT_ALGORITHM: str = "HS256"
    STUDENT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
