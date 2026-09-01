from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from app.core.database import get_session
from app.core.security import get_current_student, get_current_admin, create_student_access_token
from app.schemas.student import StudentCreate, StudentResponse, StudentAuthResponse
from app.schemas.auth import AdminResponse
from app.models.student import Student
from app.crud import students as student_crud
from app.core.exceptions import NotFoundException

router = APIRouter(prefix="/students", tags=["Students"])


@router.post(
    "/register",
    response_model=StudentAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a student and issue a signed student access token"
)
def register_student(
    student_in: StudentCreate,
    session: Session = Depends(get_session)
):
    """
    Register a student for the live quiz:
    - If new, creates student profile.
    - If existing, retrieves existing student profile (idempotent).
    - Generates and returns a signed student JWT access token for subsequent quiz API calls and WebSocket connections.
    """
    student, is_new = student_crud.register_or_get_student(session, student_in)
    access_token = create_student_access_token(student_id=student.id)

    return StudentAuthResponse(
        student=StudentResponse.model_validate(student),
        access_token=access_token,
        token_type="bearer"
    )


@router.get(
    "/me",
    response_model=StudentResponse,
    summary="Get profile of currently authenticated student"
)
def get_student_me(current_student: Student = Depends(get_current_student)):
    """Return the authenticated student's profile."""
    return current_student


@router.get(
    "",
    response_model=List[StudentResponse],
    summary="List all registered students (Admin Only)"
)
def list_students(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    admin: AdminResponse = Depends(get_current_admin)
):
    """Protected endpoint for Admin to view the full participant list."""
    return student_crud.get_all_students(session, skip=skip, limit=limit)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get student by ID (Admin Only)"
)
def get_student(
    student_id: int,
    session: Session = Depends(get_session),
    admin: AdminResponse = Depends(get_current_admin)
):
    """Protected endpoint for Admin to view an individual student profile."""
    student = student_crud.get_student_by_id(session, student_id)
    if not student:
        raise NotFoundException(f"Student with ID {student_id} not found.")
    return student
