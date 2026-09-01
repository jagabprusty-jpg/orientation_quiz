import secrets
from fastapi import APIRouter, Depends, status
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_password, create_access_token, get_current_admin
from app.schemas.auth import LoginRequest, TokenResponse, AdminResponse

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login to acquire JWT access token"
)
def admin_login(login_data: LoginRequest):
    """
    Authenticate admin credentials:
    - Validates username in constant-time.
    - Verifies password against bcrypt hash.
    - Returns JWT Bearer token on success.
    - Returns generic HTTP 401 on failure without revealing which field was incorrect.
    """
    # Verify username in constant time
    is_username_valid = secrets.compare_digest(
        login_data.username.encode("utf-8"),
        settings.ADMIN_USERNAME.encode("utf-8")
    )

    # Verify password against stored bcrypt hash
    is_password_valid = verify_password(
        login_data.password,
        settings.ADMIN_PASSWORD_HASH
    )

    if not (is_username_valid and is_password_valid):
        raise UnauthorizedException(
            detail="Invalid username or password.",
            error_code="INVALID_CREDENTIALS"
        )

    # Issue JWT token
    access_token = create_access_token(
        data={"sub": settings.ADMIN_USERNAME, "role": "admin"}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.get(
    "/me",
    response_model=AdminResponse,
    summary="Get currently authenticated admin user"
)
def get_admin_me(current_admin: AdminResponse = Depends(get_current_admin)):
    """Return the profile of the currently authenticated admin."""
    return current_admin
