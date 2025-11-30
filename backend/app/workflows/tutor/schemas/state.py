"""State-related schemas for tutor workflow."""

from enum import Enum

from pydantic import BaseModel, Field


class TutorPhase(str, Enum):
    """Tutor workflow phases."""

    SYLLABUS_GENERATION = "syllabus_generation"
    LESSON_DELIVERY = "lesson_delivery"
    SOCRATIC_QUESTIONING = "socratic_questioning"
    READINESS_ASSESSMENT = "readiness_assessment"
    REPHRASE_EXPLANATION = "rephrase_explanation"
    SECTION_REVIEW = "section_review"
    FINAL_CHALLENGE = "final_challenge"
    REFLECTION = "reflection"
    COMPLETED = "completed"


class Message(BaseModel):
    """Message in conversation history.

    Attributes:
        role: Message role (user or assistant)
        content: Message content
        created_at: Timestamp when message was created
        metadata: Optional message metadata

    """

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    created_at: str = Field(..., description="ISO timestamp")
    metadata: dict[str, object] | None = Field(None, description="Optional metadata")
