"""Prompt building utilities for agents.

All prompt builders are pure functions for easy testing.
"""


def build_agent_user_prompt(
    content: str,
    content_type: str,
    max_length: int = 12000,
    proactive_context: str = "",
) -> str:
    """Build user prompt for agent analysis.

    Issue #300: Supports proactive memory recall context injection.
    If proactive_context is provided, it is prepended to the content.

    Args:
        content: Full content text
        content_type: Type of content (article, video, repo)
        max_length: Maximum content length to include
        proactive_context: Formatted memory context from past analyses (optional)

    Returns:
        Formatted user prompt string with optional memory context

    """
    content_preview = content[:max_length] if len(content) > max_length else content
    base_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

    # Prepend proactive context if available
    if proactive_context:
        return f"{proactive_context}\n---\n\n{base_prompt}"

    return base_prompt


def build_supervisor_user_prompt(
    system_prompt: str,
    content: str,
    content_type: str,
) -> str:
    """Build user prompt for supervisor routing.

    Args:
        system_prompt: Supervisor system prompt
        content: Sized content for supervisor
        content_type: Type of content

    Returns:
        Formatted user prompt string

    """
    return f"{system_prompt}\n\nContent Type: {content_type}\n\nContent:\n{content}"
