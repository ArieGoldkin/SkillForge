"""Message and conversation type definitions.

This module defines TypedDict structures for messages and
conversations used in tutor workflows.
"""

from typing import TypedDict


class TutorMessage(TypedDict, total=False):
    """Structure for tutor conversation messages.

    Represents a single message in a tutoring conversation,
    compatible with LangChain message formats.

    Attributes:
        role: Message role ('user', 'assistant', 'system')
        content: Message text content
        created_at: ISO timestamp when message was created
        metadata: Additional message metadata

    """

    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: str | None
    metadata: dict[str, object] | None
