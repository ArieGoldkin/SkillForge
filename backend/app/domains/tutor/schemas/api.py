"""API request/response schemas for tutor endpoints."""

from pydantic import BaseModel, Field

# Note: Response schemas use `str` for JSON serialization.
# Branded types (SessionID, AnalysisID) are for internal type safety only.


class CreateSessionRequest(BaseModel):
    """Request to create a new tutoring session.

    Attributes:
        analysis_id: Optional analysis ID to base session on
        user_level: User's skill level (beginner, intermediate, advanced)

    """

    analysis_id: str | None = Field(None, description="Optional analysis ID")
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

    session_id: str = Field(..., description="Session ID")
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

    session_id: str = Field(..., description="Session ID")
    analysis_id: str | None = Field(None, description="Optional analysis ID")
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


class TutoringTopic(BaseModel):
    """A topic available for tutoring.

    Attributes:
        id: Unique identifier for the topic
        name: Display name of the topic
        description: Detailed description of what will be covered
        complexity: Difficulty level of the topic

    """

    id: str = Field(..., description="Topic identifier")
    name: str = Field(..., description="Topic display name")
    description: str = Field(default="", description="Topic description")
    complexity: str = Field(
        default="intermediate",
        description="Topic complexity: beginner, intermediate, advanced",
    )


class TopicsResponse(BaseModel):
    """Response containing topics for a tutoring session.

    Attributes:
        analysis_id: The analysis these topics were extracted from
        analysis_title: Title of the analysis
        topics: List of available topics for tutoring

    """

    analysis_id: UUID = Field(..., description="Analysis ID")
    analysis_title: str = Field(..., description="Analysis title")
    topics: list[TutoringTopic] = Field(default_factory=list, description="Available topics")
