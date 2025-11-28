"""Prompt building utilities for workflow tasks.

All prompt builders are pure functions for easy testing.
"""


def build_synthesis_user_prompt(formatted_findings: str) -> str:
    """Build user prompt for LLM synthesis.

    Args:
        formatted_findings: Pre-formatted agent findings string

    Returns:
        Formatted user prompt string for synthesis

    """
    return f"""Analyze and synthesize the following agent findings:

{formatted_findings}

Generate a cohesive synthesis following the output format requirements.
Ensure the executive summary is 2-3 sentences and key findings are 3-7 items.
"""
