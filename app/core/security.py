from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import AdminResponse
from app.models.student import Student
from app.crud import students as student_crud

# HTTPBearer security scheme (auto_error=False so we can provide custom clean 401 error payloads)
security_scheme = HTTPBearer(auto_error=False)


# ==========================================
# Password Hashing & Verification
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt with a salt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


# ==========================================
# Admin JWT Token Management
# ==========================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed Admin JWT access token with expiration and issued-at timestamps."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": now,
        "exp": expire,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate an Admin JWT access token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(
            detail="Token has expired. Please log in again.",
            error_code="TOKEN_EXPIRED"
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedException(
            detail="Invalid authentication token.",
            error_code="INVALID_TOKEN"
        )


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> AdminResponse:
    """
    Reusable FastAPI dependency for protecting admin routes:
    - Checks Authorization header.
    - Validates Bearer scheme.
    - Validates JWT signature, expiration, and role.
    - Returns AdminResponse on success.
    - Raises HTTP 401 on missing, invalid, or expired token.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise UnauthorizedException(
            detail="Authentication token is missing. Please provide a Bearer token.",
            error_code="TOKEN_MISSING"
        )

    if not credentials or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException(
            detail="Invalid authorization scheme. Bearer token required.",
            error_code="INVALID_SCHEME"
        )

    payload = decode_access_token(credentials.credentials)

    username: Optional[str] = payload.get("sub")
    role: Optional[str] = payload.get("role")

    if not username or username != settings.ADMIN_USERNAME or role != "admin":
        raise UnauthorizedException(
            detail="Could not validate admin credentials.",
            error_code="INVALID_ADMIN_CREDENTIALS"
        )

    return AdminResponse(username=username, role=role)


# ==========================================
# Student JWT Token Management & Dependency
# ==========================================

def create_student_access_token(
    student_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed Student JWT access token.
    Contains minimal identity claims (sub, type, iat, exp).
    Contains NO sensitive personal information (no phone, no email).
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.STUDENT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": f"student:{student_id}",
        "type": "student",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.STUDENT_JWT_SECRET_KEY,
        algorithm=settings.STUDENT_JWT_ALGORITHM
    )


def decode_student_access_token(token: str) -> int:
    """
    Decode and validate a Student JWT token.
    Returns the extracted student_id on success.
    Raises UnauthorizedException on invalid signature, expiration, or type mismatch.
    """
    try:
        payload = jwt.decode(
            token,
            settings.STUDENT_JWT_SECRET_KEY,
            algorithms=[settings.STUDENT_JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(
            detail="Student token has expired. Please register again.",
            error_code="STUDENT_TOKEN_EXPIRED"
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedException(
            detail="Invalid student authentication token.",
            error_code="INVALID_STUDENT_TOKEN"
        )

    sub: Optional[str] = payload.get("sub")
    token_type: Optional[str] = payload.get("type")

    if not sub or token_type != "student" or not sub.startswith("student:"):
        raise UnauthorizedException(
            detail="Invalid student token claims.",
            error_code="INVALID_STUDENT_CLAIMS"
        )

    try:
        student_id = int(sub.split(":")[1])
        return student_id
    except (ValueError, IndexError):
        raise UnauthorizedException(
            detail="Malformed student identity in token.",
            error_code="MALFORMED_STUDENT_ID"
        )


async def get_current_student(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: Session = Depends(get_session)
) -> Student:
    """
    Reusable FastAPI dependency for authenticating student requests:
    - Reads Bearer token from Authorization header.
    - Decodes and validates student token.
    - Loads and verifies student from the database.
    - Returns the authenticated Student model instance.
    - Raises HTTP 401 on missing, invalid, or expired tokens.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise UnauthorizedException(
            detail="Student authentication token is missing. Please provide a Bearer token.",
            error_code="TOKEN_MISSING"
        )

    if not credentials or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException(
            detail="Invalid authorization scheme. Bearer token required.",
            error_code="INVALID_SCHEME"
        )

    student_id = decode_student_access_token(credentials.credentials)

    student = student_crud.get_student_by_id(session, student_id)
    if not student:
        raise UnauthorizedException(
            detail="Student account not found or deregistered.",
            error_code="STUDENT_NOT_FOUND"
        )

    return student
