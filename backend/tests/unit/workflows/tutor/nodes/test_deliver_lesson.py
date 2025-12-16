"""Unit tests for deliver_lesson node."""

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_with_syllabus():
    """Sample tutor state with syllabus."""
    import uuid
    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus={
            "title": "Test Syllabus",
            "sections": [
                {
                    "title": "Section 1",
                    "lessons": [
                        {
                            "title": "Lesson 1",
                            "concept": "Test Concept",
                            "explanation": "Test explanation",
                        }
                    ],
                }
            ],
        },
        current_section=0,
        current_lesson=0,
        current_phase="lesson_delivery",
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


@pytest.mark.asyncio
async def test_deliver_lesson_generates_content(sample_tutor_state_with_syllabus):
    """Test that deliver_lesson generates lesson content."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domains.tutor.workflows.nodes.deliver_lesson import deliver_lesson

    mock_response = MagicMock()
    mock_response.content = "This is a lesson about the concept."
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.domains.tutor.workflows.nodes.deliver_lesson.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch(
            "app.db.repositories.tutor_message_repository.TutorMessageRepository"
        ) as mock_repo_class,
        patch("app.domains.tutor.workflows.nodes.deliver_lesson._emit_tutor_event", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_message = MagicMock()
        mock_message.created_at = MagicMock()
        mock_message.created_at.isoformat = lambda: "2025-01-01T00:00:00"
        mock_repo.save_message = AsyncMock(return_value=mock_message)

        result = await deliver_lesson(sample_tutor_state_with_syllabus)

        assert "last_assistant_response" in result
        assert result["last_assistant_response"] == "This is a lesson about the concept."
        assert result["current_phase"] == "socratic_questioning"
