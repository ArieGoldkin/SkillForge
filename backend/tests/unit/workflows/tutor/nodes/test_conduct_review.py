"""Unit tests for conduct_review node."""

import pytest

from app.domains.tutor.workflows.state import TutorState


@pytest.fixture
def sample_tutor_state_for_review():
    """Sample tutor state for section review."""
    import uuid
    return TutorState(
        session_id=str(uuid.uuid4()),
        analysis_id=None,
        syllabus={
            "sections": [
                {
                    "title": "Section 1",
                    "lessons": [
                        {"concept": "Concept 1"},
                        {"concept": "Concept 2"},
                    ],
                }
            ]
        },
        current_section=0,
        current_lesson=1,  # Last lesson in section
        current_phase="section_review",
        user_level="intermediate",
        understanding_scores={"section_0_lesson_0": 0.8, "section_0_lesson_1": 0.9},
        conversation_history=[],
        conversation_summary=None,
        last_user_message=None,
        last_assistant_response=None,
        user_ready=True,
        attempts_current_lesson=0,
        session_metadata=None,
    )


@pytest.mark.asyncio
async def test_conduct_review_creates_quiz(sample_tutor_state_for_review):
    """Test that conduct_review creates a section quiz."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.domains.tutor.workflows.nodes.conduct_review import conduct_review

    mock_response = MagicMock()
    mock_response.content = "Quiz: 1. What is Concept 1? 2. Explain Concept 2..."
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=mock_response)

    with (
        patch("app.domains.tutor.workflows.nodes.conduct_review.get_chat_model", return_value=mock_model),
        patch("app.db.session.get_session_factory") as mock_factory,
        patch("app.domains.tutor.workflows.nodes.conduct_review.TutorMessageRepository") as mock_repo_class,
        patch("app.domains.tutor.workflows.nodes.conduct_review._emit_tutor_event", new_callable=AsyncMock),
    ):
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        mock_repo_instance = MagicMock()
        mock_repo_class.return_value = mock_repo_instance
        mock_message_obj = MagicMock()
        mock_message_obj.created_at = MagicMock()
        mock_message_obj.created_at.isoformat = lambda: "2025-01-01T00:00:00"
        mock_repo_instance.save_message = AsyncMock(return_value=mock_message_obj)

        result = await conduct_review(sample_tutor_state_for_review)

        assert "last_assistant_response" in result
        assert (
            "quiz" in result["last_assistant_response"].lower()
            or "question" in result["last_assistant_response"].lower()
        )
        assert result["current_phase"] == "section_review"
