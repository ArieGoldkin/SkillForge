"""Unit tests for final_challenge node."""

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_for_challenge():
    """Sample tutor state for final challenge."""
    import uuid
    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus={
            "sections": [
                {"title": "Section 1", "lessons": [{"concept": "Concept 1"}]},
                {"title": "Section 2", "lessons": [{"concept": "Concept 2"}]},
            ]
        },
        current_section=1,  # Last section
        current_lesson=0,
        current_phase="final_challenge",
        user_level="intermediate",
        understanding_scores={"section_0_lesson_0": 0.8, "section_1_lesson_0": 0.9},
        conversation_history=[],
        conversation_summary=None,
        last_user_message=None,
        last_assistant_response=None,
        user_ready=True,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.mark.asyncio
async def test_final_challenge_creates_integrative_problem(sample_tutor_state_for_challenge):
    """Test that final_challenge creates an integrative problem."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domains.tutor.workflows.nodes.final_challenge import final_challenge

    mock_response = MagicMock()
    mock_response.content = "Challenge: Create a solution that combines Concept 1 and Concept 2..."
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.workflows.tutor.nodes.final_challenge.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.workflows.tutor.nodes.final_challenge.TutorMessageRepository"
        ) as mock_repo_class,
        patch(
            "app.workflows.tutor.nodes.final_challenge._emit_tutor_event", new_callable=AsyncMock
        ),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = MagicMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_message_obj = MagicMock()
        mock_message_obj.created_at = MagicMock()
        mock_message_obj.created_at.isoformat = lambda: "2025-01-01T00:00:00"
        mock_repo_instance.save_message = AsyncMock(return_value=mock_message_obj)

        result = await final_challenge(sample_tutor_state_for_challenge)

        assert "last_assistant_response" in result
        assert (
            "challenge" in result["last_assistant_response"].lower()
            or "problem" in result["last_assistant_response"].lower()
        )
        assert result["current_phase"] == "reflection"
