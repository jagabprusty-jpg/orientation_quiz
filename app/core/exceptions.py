from typing import Optional, Dict
from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "APP_ERROR",
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, error_code=error_code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource conflict", error_code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, error_code=error_code)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Invalid request", error_code: str = "BAD_REQUEST"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, error_code=error_code)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Could not validate credentials", error_code: str = "UNAUTHORIZED"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Operation not permitted", error_code: str = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, error_code=error_code)


class RoundNotActiveException(BadRequestException):
    def __init__(self, detail: str = "Quiz round is not currently active"):
        super().__init__(detail=detail, error_code="ROUND_NOT_ACTIVE")


class DuplicateAnswerException(ConflictException):
    def __init__(self, detail: str = "Student has already submitted an answer for this round"):
        super().__init__(detail=detail, error_code="DUPLICATE_ANSWER")
