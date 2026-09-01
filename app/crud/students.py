from typing import List, Optional
from sqlmodel import Session, select
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate
from app.core.exceptions import ConflictException


def get_student_by_id(session: Session, student_id: int) -> Optional[Student]:
    """Retrieve student by primary key ID."""
    return session.get(Student, student_id)


def get_student_by_registration_number(session: Session, reg_no: str) -> Optional[Student]:
    """Retrieve student by unique registration number."""
    statement = select(Student).where(Student.registration_number == reg_no)
    return session.exec(statement).first()


def get_student_by_email(session: Session, email: str) -> Optional[Student]:
    """Retrieve student by unique email address."""
    statement = select(Student).where(Student.email == email)
    return session.exec(statement).first()


def get_all_students(session: Session, skip: int = 0, limit: int = 100) -> List[Student]:
    """Retrieve paginated list of students."""
    statement = select(Student).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def create_student(session: Session, student_in: StudentCreate) -> Student:
    """Create a new student with validation against duplicates."""
    # Check registration number
    existing_reg = get_student_by_registration_number(session, student_in.registration_number)
    if existing_reg:
        raise ConflictException(
            f"Registration number '{student_in.registration_number}' is already registered."
        )

    # Check email
    existing_email = get_student_by_email(session, student_in.email)
    if existing_email:
        raise ConflictException(
            f"Email '{student_in.email}' is already registered."
        )

    db_student = Student(
        name=student_in.name,
        registration_number=student_in.registration_number,
        branch=student_in.branch,
        phone=student_in.phone,
        email=student_in.email,
    )
    session.add(db_student)
    session.commit()
    session.refresh(db_student)
    return db_student


def register_or_get_student(session: Session, student_in: StudentCreate) -> tuple[Student, bool]:
    """
    Register a student if not already present.
    If matching student exists by registration_number or email:
      - If exact match or consistent, returns (student, created=False).
      - If conflict (e.g. reg_no belongs to one student and email to another), raises ConflictException.
    """
    by_reg = get_student_by_registration_number(session, student_in.registration_number)
    by_email = get_student_by_email(session, student_in.email)

    if by_reg and by_email:
        if by_reg.id != by_email.id:
            raise ConflictException(
                "Registration number and email belong to two different registered students."
            )
        # Update fields if student re-submitted updated phone/name/branch
        by_reg.name = student_in.name
        by_reg.branch = student_in.branch
        by_reg.phone = student_in.phone
        session.add(by_reg)
        session.commit()
        session.refresh(by_reg)
        return by_reg, False

    if by_reg:
        # Registration number exists with different email
        if by_reg.email != student_in.email:
            raise ConflictException(
                f"Registration number '{student_in.registration_number}' is already registered with a different email."
            )
        by_reg.name = student_in.name
        by_reg.branch = student_in.branch
        by_reg.phone = student_in.phone
        session.add(by_reg)
        session.commit()
        session.refresh(by_reg)
        return by_reg, False

    if by_email:
        # Email exists with different registration number
        if by_email.registration_number != student_in.registration_number:
            raise ConflictException(
                f"Email '{student_in.email}' is already registered with a different registration number."
            )
        by_email.name = student_in.name
        by_email.branch = student_in.branch
        by_email.phone = student_in.phone
        session.add(by_email)
        session.commit()
        session.refresh(by_email)
        return by_email, False

    # New student
    new_student = Student(
        name=student_in.name,
        registration_number=student_in.registration_number,
        branch=student_in.branch,
        phone=student_in.phone,
        email=student_in.email,
    )
    session.add(new_student)
    session.commit()
    session.refresh(new_student)
    return new_student, True
