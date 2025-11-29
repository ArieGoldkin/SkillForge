"""Unit tests for guide_reflection node."""

import pytest

from app.workflows.tutor.state import TutorState


@pytest.fixture
def sample_tutor_state_for_reflection():
    """Sample tutor state for reflection."""
    import uuid

    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus={
            "sections": [
                {"title": "Section 1", "lessons": [{"concept": "Concept 1"}]},
            ]
        },
        current_section=0,
        current_lesson=0,
        current_phase="reflection",
        user_level="intermediate",
        understanding_scores={"section_0_lesson_0": 0.9},
        conversation_history=[],
        conversation_summary=None,
        last_user_message=None,
        last_assistant_response=None,
        user_ready=True,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.mark.asyncio
async def test_guide_reflection_provides_guidance_and_marks_complete(
    sample_tutor_state_for_reflection,
):
    """Test that guide_reflection provides guidance and marks session complete."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.workflows.tutor.nodes.guide_reflection import guide_reflection

    mock_response = MagicMock()
    mock_response.content = "Great job! Here are real-world applications..."
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.workflows.tutor.nodes.guide_reflection.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.workflows.tutor.nodes.guide_reflection.TutorMessageRepository"
        ) as mock_message_repo_class,
        patch(
            "app.workflows.tutor.nodes.guide_reflection.TutorSessionRepository"
        ) as mock_session_repo_class,
        patch(
            "app.workflows.tutor.nodes.guide_reflection._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_message_repo_instance = MagicMock()
        mock_message_repo_class.return_value = mock_message_repo_instance
        mock_session_repo_instance = MagicMock()
        mock_session_repo_class.return_value = mock_session_repo_instance
        mock_message_obj = MagicMock()
        mock_message_obj.created_at = MagicMock()
        mock_message_obj.created_at.isoformat = lambda: "2025-01-01T00:00:00"
        mock_message_repo_instance.save_message = AsyncMock(return_value=mock_message_obj)
        mock_session_obj = MagicMock()
        mock_session_obj.current_phase = "completed"
        mock_session_repo_instance.update_session_state = AsyncMock(return_value=mock_session_obj)

        result = await guide_reflection(sample_tutor_state_for_reflection)

        assert "last_assistant_response" in result
        assert result["current_phase"] == "completed"
        # Verify session was marked as completed
        mock_session_repo_instance.update_session_state.assert_called_once()
        call_args = mock_session_repo_instance.update_session_state.call_args
        assert call_args[1]["status"] == "completed"
        assert call_args[1]["current_phase"] == "completed"
