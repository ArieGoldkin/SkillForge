"""Context management for tutor workflow.

Implements sliding window and conversation summarization for efficient
context management within token budget.
"""

from app.core.logging import get_logger
from app.workflows.tutor.config import SLIDING_WINDOW_SIZE, SUMMARY_THRESHOLD, TOKEN_BUDGET
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


def build_conversation_context(state: TutorState) -> str:
    """Build conversation context using sliding window + summarization.

    Strategy:
    - Last N messages kept verbatim (sliding window)
    - Older messages summarized
    - Total context within token budget

    Args:
        state: Current tutor state

    Returns:
        Formatted conversation context string

    """
    conversation_history = state.get("conversation_history", [])
    conversation_summary = state.get("conversation_summary")

    if not conversation_history:
        # No history yet, return summary if available
        if conversation_summary:
            return f"Previous conversation summary: {conversation_summary}\n\n"
        return ""

    # Get last N messages (sliding window)
    recent_messages = conversation_history[-SLIDING_WINDOW_SIZE:]

    # Build context
    context_parts = []

    # Add summary of older messages if we have more than window size
    if len(conversation_history) > SLIDING_WINDOW_SIZE and conversation_summary:
        context_parts.append(f"Previous conversation summary: {conversation_summary}\n\n")

    # Add recent messages verbatim
    context_parts.append("Recent conversation:\n")
    for msg in recent_messages:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            context_parts.append(f"{role}: {content}\n")

    return "".join(context_parts)


def should_summarize(conversation_history: list[dict[str, object]]) -> bool:
    """Check if conversation should be summarized.

    Args:
        conversation_history: List of conversation messages

    Returns:
        True if conversation exceeds threshold and should be summarized

    """
    return len(conversation_history) > SUMMARY_THRESHOLD


async def summarize_conversation(
    conversation_history: list[dict[str, object]],
    current_topic: str,
) -> str:
    """Summarize older conversation messages.

    Uses LLM to create a concise summary of conversation history
    while preserving key learning points and user understanding level.

    Args:
        conversation_history: Full conversation history
        current_topic: Current topic/concept being taught

    Returns:
        Summarized conversation text

    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.model_factory import get_chat_model

    # Build conversation text
    conversation_text = "\n".join(
        [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in conversation_history]
    )

    prompt = f"""Summarize this tutoring conversation, preserving:
1. Key concepts covered
2. User's understanding level
3. Areas where user struggled
4. Current learning progress

Current Topic: {current_topic}

Conversation:
{conversation_text}

Provide a concise summary (2-3 sentences) that captures the essential learning context."""

    model = get_chat_model()
    messages = [
        SystemMessage(content="You are an expert at summarizing educational conversations."),
        HumanMessage(content=prompt),
    ]

    response = await model.ainvoke(messages)
    summary_text: str
    if hasattr(response, "content"):
        content = response.content
        summary_text = content if isinstance(content, str) else str(content)
    else:
        summary_text = str(response)

    logger.debug(
        "tutor_conversation_summarized",
        original_length=len(conversation_history),
        summary_length=len(summary_text),
    )

    return summary_text
