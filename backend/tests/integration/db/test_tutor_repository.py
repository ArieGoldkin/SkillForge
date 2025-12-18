"""Integration tests for tutor repositories.

These tests verify database CRUD operations for tutor sessions and messages.
They require a real database connection to test persistence, transactions, and relationships.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tutor.repositories.message_repository import TutorMessageRepository
from app.domains.tutor.repositories.session_repository import TutorSessionRepository


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_session(db_session: AsyncSession):
    """Test creating a tutoring session."""
    repo = TutorSessionRepository(session=db_session)

    session = await repo.create_session(
        user_level="intermediate",
    )

    assert session is not None
    assert session.id is not None
    assert session.status == "active"
    assert session.user_level == "intermediate"
    assert session.current_section == 0
    assert session.current_lesson == 0
    assert session.current_phase == "syllabus_generation"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_session_with_analysis_id(db_session: AsyncSession):
    """Test creating session with analysis_id."""
    from app.db.models.analysis import Analysis

    analysis = Analysis(
        url="https://example.com/article",
        content_type="article",
        status="complete",
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    repo = TutorSessionRepository(session=db_session)
    session = await repo.create_session(
        analysis_id=analysis.id,
        user_level="advanced",
    )

    assert session.analysis_id == analysis.id
    assert session.user_level == "advanced"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_session(db_session: AsyncSession):
    """Test getting a session by ID."""
    repo = TutorSessionRepository(session=db_session)

    created = await repo.create_session(user_level="beginner")
    session_id = created.id

    retrieved = await repo.get_session(session_id)

    assert retrieved is not None
    assert retrieved.id == session_id
    assert retrieved.user_level == "beginner"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_session_not_found(db_session: AsyncSession):
    """Test getting non-existent session returns None."""
    repo = TutorSessionRepository(session=db_session)

    fake_id = uuid.uuid4()
    result = await repo.get_session(fake_id)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_session_with_messages(db_session: AsyncSession):
    """Test getting session with messages."""
    session_repo = TutorSessionRepository(session=db_session)
    message_repo = TutorMessageRepository(session=db_session)

    session = await session_repo.create_session(user_level="intermediate")

    await message_repo.save_message(session.id, "user", "Hello")
    await message_repo.save_message(session.id, "assistant", "Hi there!")

    retrieved_session, messages = await message_repo.get_session_with_messages(session.id)

    assert retrieved_session.id == session.id
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_save_message(db_session: AsyncSession):
    """Test saving a message."""
    session_repo = TutorSessionRepository(session=db_session)
    message_repo = TutorMessageRepository(session=db_session)

    session = await session_repo.create_session()

    message = await message_repo.save_message(
        session.id,
        role="user",
        content="Test message",
        message_metadata={"test": "data"},
    )

    assert message.id is not None
    assert message.session_id == session.id
    assert message.role == "user"
    assert message.content == "Test message"
    assert message.message_metadata == {"test": "data"}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_session_state(db_session: AsyncSession):
    """Test updating session state."""
    repo = TutorSessionRepository(session=db_session)

    session = await repo.create_session()

    syllabus = {
        "title": "Test Syllabus",
        "sections": [{"title": "Section 1", "lessons": []}],
    }

    updated = await repo.update_session_state(
        session.id,
        syllabus=syllabus,
        current_section=1,
        current_lesson=2,
        current_phase="lesson_delivery",
        understanding_scores={"concept1": 0.8},
    )

    assert updated.syllabus == syllabus
    assert updated.current_section == 1
    assert updated.current_lesson == 2
    assert updated.current_phase == "lesson_delivery"
    assert updated.understanding_scores == {"concept1": 0.8}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_session_status_to_completed(db_session: AsyncSession):
    """Test updating session status to completed sets completed_at."""
    repo = TutorSessionRepository(session=db_session)

    session = await repo.create_session()
    assert session.completed_at is None

    updated = await repo.update_session_state(
        session.id,
        status="completed",
    )

    assert updated.status == "completed"
    assert updated.completed_at is not None
