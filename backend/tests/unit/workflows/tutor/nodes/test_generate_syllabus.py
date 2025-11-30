"""Unit tests for generate_syllabus node."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.tutor.state import TutorState


@pytest.fixture
def sample_tutor_state():
    """Sample tutor state for testing."""
    import uuid

    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus=None,
        current_section=0,
        current_lesson=0,
        current_phase="syllabus_generation",
        user_level="intermediate",
        understanding_scores={},
        conversation_history=[],
        conversation_summary=None,
        last_user_message=None,
        last_assistant_response=None,
        user_ready=False,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.fixture
def mock_llm_response():
    """Mock LLM response with syllabus JSON."""
    syllabus = {
        "title": "Test Syllabus",
        "description": "Test description",
        "sections": [
            {
                "title": "Section 1",
                "description": "Section 1 description",
                "lessons": [
                    {
                        "title": "Lesson 1",
                        "concept": "Concept 1",
                        "explanation": "Explanation 1",
                    }
                ],
            }
        ],
    }
    response = MagicMock()
    response.content = json.dumps(syllabus)
    return response


@pytest.mark.asyncio
async def test_generate_syllabus_creates_syllabus(sample_tutor_state, mock_llm_response):
    """Test that generate_syllabus creates a syllabus."""
    from app.workflows.tutor.nodes.generate_syllabus import generate_syllabus

    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)

    with (
        patch(
            "app.workflows.tutor.nodes.generate_syllabus.get_chat_model", return_value=mock_model
        ),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.db.repositories.tutor_session_repository.TutorSessionRepository"
        ) as mock_repo_class,
        patch(
            "app.services.tutor.analysis_service.get_analysis_summary", new_callable=AsyncMock
        ) as mock_analysis,
        patch(
            "app.workflows.tutor.nodes.generate_syllabus._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = AsyncMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_repo_instance.update_session_state = AsyncMock()
        mock_analysis.return_value = None

        result = await generate_syllabus(sample_tutor_state)

        assert "syllabus" in result
        assert result["syllabus"] is not None
        assert "current_phase" in result
        assert result["current_phase"] == "lesson_delivery"


@pytest.mark.asyncio
async def test_generate_syllabus_handles_parse_error(sample_tutor_state):
    """Test that generate_syllabus handles JSON parse errors gracefully."""
    from app.workflows.tutor.nodes.generate_syllabus import generate_syllabus

    # Mock LLM response with invalid JSON
    mock_response = MagicMock()
    mock_response.content = "Invalid JSON response"
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.workflows.tutor.nodes.generate_syllabus.get_chat_model", return_value=mock_model
        ),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.db.repositories.tutor_session_repository.TutorSessionRepository"
        ) as mock_repo_class,
        patch(
            "app.services.tutor.analysis_service.get_analysis_summary", new_callable=AsyncMock
        ) as mock_analysis,
        patch(
            "app.workflows.tutor.nodes.generate_syllabus._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = AsyncMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_repo_instance.update_session_state = AsyncMock()
        mock_analysis.return_value = None

        # Should not raise, should create fallback syllabus
        result = await generate_syllabus(sample_tutor_state)

        assert "syllabus" in result
        assert result["syllabus"] is not None
        # Fallback syllabus should have basic structure
        assert "sections" in result["syllabus"]
