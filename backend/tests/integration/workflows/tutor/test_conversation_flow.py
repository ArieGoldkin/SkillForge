"""Integration tests for tutor conversation flow."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_session_endpoint(client):
    """Test creating a tutoring session."""
    response = client.post(
        "/api/v1/tutor/sessions",
        json={
            "user_level": "intermediate",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert "status" in data
    assert "sse_endpoint" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_session_endpoint(client, db_session):
    """Test getting a session (for resume)."""
    from app.domains.tutor.repositories.session_repository import TutorSessionRepository

    session_repo = TutorSessionRepository(session=db_session)
    session = await session_repo.create_session(user_level="beginner")

    response = client.get(f"/api/v1/tutor/sessions/{session.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(session.id)
    assert data["status"] == "active"
    assert data["user_level"] == "beginner"
    assert "messages" in data


@pytest.mark.asyncio
async def test_update_session_status(client, db_session):
    """Test updating session status (for exit)."""
    from app.domains.tutor.repositories.session_repository import TutorSessionRepository

    session_repo = TutorSessionRepository(session=db_session)
    session = await session_repo.create_session()

    response = client.patch(
        f"/api/v1/tutor/sessions/{session.id}",
        json={"status": "completed"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_send_message_endpoint(client, db_session):
    """Test sending a message in a session."""
    from app.domains.tutor.repositories.session_repository import TutorSessionRepository

    session_repo = TutorSessionRepository(session=db_session)
    session = await session_repo.create_session()

    response = client.post(
        f"/api/v1/tutor/sessions/{session.id}/messages",
        json={"content": "Hello, I want to learn"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "message_id" in data
    assert data["status"] == "sent"
