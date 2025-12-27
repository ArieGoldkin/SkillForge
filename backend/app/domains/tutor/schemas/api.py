"""API request/response schemas for tutor endpoints."""

from pydantic import BaseModel, Field

from app.core.branded_ids import AnalysisID, SessionID


class CreateSessionRequest(BaseModel):
    """Request to create a new tutoring session.

    Attributes:
        analysis_id: Optional analysis ID to base session on
        user_level: User's skill level (beginner, intermediate, advanced)

    """

    analysis_id: AnalysisID | None = Field(None, description="Optional analysis ID")
    user_level: str = Field(
        default="intermediate",
        description="User skill level: beginner, intermediate, advanced",
    )


class CreateSessionResponse(BaseModel):
    """Response from creating a tutoring session.

    Attributes:
        session_id: Created session ID
        status: Session status
        sse_endpoint: SSE endpoint for streaming updates

    """

    session_id: SessionID = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    sse_endpoint: str = Field(..., description="SSE endpoint path")


class GetSessionResponse(BaseModel):
    """Response from getting a tutoring session.

    Attributes:
        session_id: Session ID
        analysis_id: Optional analysis ID
        status: Session status
        syllabus: Generated syllabus (if available)
        current_section: Current section index
        current_lesson: Current lesson index
        current_phase: Current workflow phase
        user_level: User skill level
        messages: Conversation history
        started_at: Session start timestamp
        completed_at: Optional completion timestamp

    """

    session_id: SessionID = Field(..., description="Session ID")
    analysis_id: AnalysisID | None = Field(None, description="Optional analysis ID")
    status: str = Field(..., description="Session status")
    syllabus: dict[str, object] | None = Field(None, description="Generated syllabus")
    current_section: int = Field(..., description="Current section index")
    current_lesson: int = Field(..., description="Current lesson index")
    current_phase: str = Field(..., description="Current workflow phase")
    user_level: str = Field(..., description="User skill level")
    messages: list[dict[str, object]] = Field(..., description="Conversation history")
    started_at: str = Field(..., description="ISO timestamp")
    completed_at: str | None = Field(None, description="Optional completion timestamp")


class SendMessageRequest(BaseModel):
    """Request to send a message in a tutoring session.

    Attributes:
        content: Message content from user

    """

    content: str = Field(..., description="User message content")


class UpdateSessionRequest(BaseModel):
    """Request to update a tutoring session.

    Attributes:
        status: New status (active, completed, abandoned)

    """

    status: str = Field(..., description="Session status: active, completed, abandoned")
