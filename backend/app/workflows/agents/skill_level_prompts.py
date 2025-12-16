"""Skill level-specific prompt instructions for agents.

This module provides centralized skill level instructions that can be injected
into agent prompts to personalize analysis output based on user experience level.
"""

SKILL_LEVEL_INSTRUCTIONS = {
    "beginner": """
TARGET AUDIENCE: Beginner Developer
- Explain technical terms on first use
- Break complex steps into smaller sub-steps
- Include "Why this matters" context for key decisions
- Warn about common mistakes and pitfalls
- Provide copy-paste ready code snippets
- Use simple, clear language
- Assume limited prior knowledge
""",
    "intermediate": """
TARGET AUDIENCE: Intermediate Developer
- Assume familiarity with core concepts
- Focus on best practices and trade-offs
- Include alternative approaches when relevant
- Reference official documentation for deep dives
- Balance detail with conciseness
- Mention edge cases without over-explaining
""",
    "expert": """
TARGET AUDIENCE: Expert Developer
- Focus on edge cases and advanced patterns
- Include performance optimizations and architectural implications
- Discuss trade-offs at scale
- Skip basic explanations
- Mention pitfalls only for non-obvious cases
- Assume deep technical knowledge
- Be concise - provide insights, not tutorials
""",
}


def get_skill_level_instructions(skill_level: str) -> str:
    r"""Get prompt instructions for the given skill level.

    Args:
        skill_level: One of "beginner", "intermediate", "expert"

    Returns:
        Skill level-specific instructions to inject into agent prompts

    Raises:
        ValueError: If skill level is invalid

    Example:
        ```python
        from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions

        skill_level = state.get("skill_level", "intermediate")
        instructions = get_skill_level_instructions(skill_level)
        full_prompt = f"{BASE_PROMPT}\n\n{instructions}\n\n{TASK_SPECIFIC}"
        ```

    """
    if skill_level not in SKILL_LEVEL_INSTRUCTIONS:
        valid_levels = list(SKILL_LEVEL_INSTRUCTIONS.keys())
        msg = f"Invalid skill_level: {skill_level}. Must be one of: {valid_levels}"
        raise ValueError(msg)
    return SKILL_LEVEL_INSTRUCTIONS[skill_level]
