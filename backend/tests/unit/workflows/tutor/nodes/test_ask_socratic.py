"""Unit tests for ask_socratic node."""

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_with_message():
    """Sample tutor state with user message."""
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
        current_phase="socratic_questioning",
        user_level="intermediate",
        understanding_scores={},
        conversation_history=[],
        conversation_summary=None,
        last_user_message="I understand the concept",
        last_assistant_response=None,
        user_ready=False,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.mark.asyncio
async def test_ask_socratic_generates_question(sample_tutor_state_with_message):
    """Test that ask_socratic generates a Socratic question."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domains.tutor.workflows.nodes.ask_socratic import ask_socratic

    mock_response = MagicMock()
    mock_response.content = "Can you explain how this concept applies in practice?"
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.domains.tutor.workflows.nodes.ask_socratic.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.db.repositories.tutor_message_repository.TutorMessageRepository"
        ) as mock_repo_class,
        patch("app.domains.tutor.workflows.nodes.ask_socratic._emit_tutor_event", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_message = MagicMock()
        mock_message.created_at = MagicMock()
        mock_message.created_at.isoformat = lambda: "2025-01-01T00:00:00"
        mock_repo.save_message = AsyncMock(return_value=mock_message)

        result = await ask_socratic(sample_tutor_state_with_message)

        assert "last_assistant_response" in result
        assert (
            "question" in result["last_assistant_response"].lower()
            or "explain" in result["last_assistant_response"].lower()
        )
        assert result["current_phase"] == "readiness_assessment"
