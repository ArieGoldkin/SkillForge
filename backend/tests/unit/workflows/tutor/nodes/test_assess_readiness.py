"""Unit tests for assess_readiness node."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_for_assessment():
    """Sample tutor state for readiness assessment."""
    import uuid

@pytest.mark.unit

    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus={
            "sections": [
                {
                    "lessons": [
                        {
                            "concept": "Test Concept",
                        }
                    ]
                }
            ]
        },
        current_section=0,
        current_lesson=0,
        current_phase="readiness_assessment",
        user_level="intermediate",
        understanding_scores={},
        conversation_history=[],
        conversation_summary=None,
        last_user_message="I think I understand now",
        last_assistant_response=None,
        user_ready=False,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.fixture
def mock_assessment_response():
    """Mock LLM response with assessment JSON."""
    assessment = {
        "user_ready": True,
        "confidence_score": 0.85,
        "reasoning": "User demonstrates understanding",
        "suggested_action": "move_on",
    }
    response = MagicMock()
    response.content = json.dumps(assessment)
    return response


@pytest.mark.asyncio
async def test_assess_readiness_evaluates_understanding(
    sample_tutor_state_for_assessment, mock_assessment_response
):
    """Test that assess_readiness evaluates user understanding."""
    from app.domains.tutor.workflows.nodes.assess_readiness import assess_readiness

    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_assessment_response)

    with (
        patch("app.workflows.tutor.nodes.assess_readiness.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.workflows.tutor.nodes.assess_readiness.TutorSessionRepository"
        ) as mock_repo_class,
        patch(
            "app.workflows.tutor.nodes.assess_readiness._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = MagicMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_session_obj = MagicMock()
        mock_repo_instance.get_session = AsyncMock(return_value=mock_session_obj)
        mock_repo_instance.update_session_state = AsyncMock(return_value=mock_session_obj)

        result = await assess_readiness(sample_tutor_state_for_assessment)

        assert "user_ready" in result
        assert result["user_ready"] is True
        assert "understanding_scores" in result
        assert "attempts_current_lesson" in result
        assert result["attempts_current_lesson"] == 1  # Incremented


@pytest.mark.asyncio
async def test_assess_readiness_handles_parse_error(sample_tutor_state_for_assessment):
    """Test that assess_readiness handles JSON parse errors gracefully."""
    from app.domains.tutor.workflows.nodes.assess_readiness import assess_readiness

    # Mock LLM response with invalid JSON
    mock_response = MagicMock()
    mock_response.content = "Invalid JSON"
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.workflows.tutor.nodes.assess_readiness.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.workflows.tutor.nodes.assess_readiness.TutorSessionRepository"
        ) as mock_repo_class,
        patch(
            "app.workflows.tutor.nodes.assess_readiness._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = MagicMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_session_obj = MagicMock()
        mock_repo_instance.get_session = AsyncMock(return_value=mock_session_obj)
        mock_repo_instance.update_session_state = AsyncMock(return_value=mock_session_obj)

        # Should not raise, should use fallback assessment
        result = await assess_readiness(sample_tutor_state_for_assessment)

        assert "user_ready" in result
        # Fallback should be conservative (not ready)
        assert result["user_ready"] is False
