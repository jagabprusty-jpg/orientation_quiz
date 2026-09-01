import sqlite3
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.core.database import get_session
from app.core.security import create_access_token, create_student_access_token
from app.core.config import settings


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency override for database session."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="admin_auth_headers")
def admin_auth_headers_fixture() -> dict:
    """Provide a valid Bearer Authorization header for admin requests."""
    token = create_access_token(data={"sub": settings.ADMIN_USERNAME, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="make_student_auth_headers")
def make_student_auth_headers_fixture():
    """Factory fixture to create Authorization headers for any student ID."""
    def _make(student_id: int) -> dict:
        token = create_student_access_token(student_id=student_id)
        return {"Authorization": f"Bearer {token}"}
    return _make
