"""Prompt building utilities for agents.

All prompt builders are pure functions for easy testing.
"""


def build_agent_user_prompt(
    content: str,
    content_type: str,
    max_length: int = 12000,
) -> str:
    """Build user prompt for agent analysis.

    Args:
        content: Full content text
        content_type: Type of content (article, video, repo)
        max_length: Maximum content length to include

    Returns:
        Formatted user prompt string

    """
    content_preview = content[:max_length] if len(content) > max_length else content
    return f"Content Type: {content_type}\n\nContent:\n{content_preview}"


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
