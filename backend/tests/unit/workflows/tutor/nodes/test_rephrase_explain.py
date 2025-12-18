"""Unit tests for rephrase_explain node."""

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_for_rephrase():
    """Sample tutor state for rephrasing."""
    import uuid

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
        current_phase="rephrase_explanation",
        user_level="intermediate",
        understanding_scores={},
        conversation_history=[],
        conversation_summary=None,
        last_user_message="I don't understand",
        last_assistant_response=None,
        user_ready=False,
        attempts_current_lesson=1,
        session_metadata=None,
    )


@pytest.mark.asyncio
async def test_rephrase_explain_generates_simpler_explanation(sample_tutor_state_for_rephrase):
    """Test that rephrase_explain generates a simpler explanation."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domains.tutor.workflows.nodes.rephrase_explain import rephrase_explain

    mock_response = MagicMock()
    mock_response.content = "Let me explain this more simply..."
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.domains.tutor.workflows.nodes.rephrase_explain.get_chat_model",
            return_value=mock_model,
        ),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.domains.tutor.workflows.nodes.rephrase_explain.TutorMessageRepository"
        ) as mock_repo_class,
        patch(
            "app.domains.tutor.workflows.nodes.rephrase_explain._emit_tutor_event",
            new_callable=AsyncMock,
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

        result = await rephrase_explain(sample_tutor_state_for_rephrase)

        assert "last_assistant_response" in result
        assert (
            "simply" in result["last_assistant_response"].lower()
            or "explain" in result["last_assistant_response"].lower()
        )
        assert result["current_phase"] == "socratic_questioning"
