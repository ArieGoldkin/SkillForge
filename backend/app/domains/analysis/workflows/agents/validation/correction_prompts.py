"""Correction prompt templates for agent self-correction.

Issue #507: Provides structured prompts to guide agent retry when
initial output fails validation. These prompts help the LLM understand
what went wrong and how to fix it.

Usage:
    from app.domains.analysis.workflows.agents.validation.correction_prompts import (
        build_correction_prompt,
    )

    prompt = build_correction_prompt(
        issues=["Only 2 insights, need >= 3"],
        correction_hints=["Provide at least 3 unique insights"],
        attempt_number=2,
    )
"""

from typing import Any

# Main correction prompt template
CORRECTION_PROMPT_TEMPLATE = """
## Self-Correction Required (Attempt {attempt_number})

Your previous response did not meet quality requirements. Please review and correct.

### Issues Found:
{issues_list}

### Correction Guidelines:
{correction_hints}

### Important:
- Address ALL issues listed above
- Provide MORE specific details from the source content
- Include concrete examples, metrics, or quotes where applicable
- Maintain the required output structure (same JSON schema)
- Do NOT use placeholder text like "TBD", "[insert]", or "to be determined"

Please generate a corrected response that addresses these issues.
"""

# Compact version for token efficiency
CORRECTION_PROMPT_COMPACT = """
## Fix Required (Attempt {attempt_number})

Issues: {issues_list}

Fix by: {correction_hints}

Regenerate with fixes. Keep same schema. No placeholders.
"""


def build_correction_prompt(
    issues: list[str],
    correction_hints: list[str],
    attempt_number: int,
    compact: bool = False,
) -> str:
    """Build correction prompt for agent retry.

    Args:
        issues: List of validation issues found in previous output
        correction_hints: Agent-specific hints for improvement
        attempt_number: Current attempt number (1-indexed, 2 means second try)
        compact: If True, use compact template to save tokens

    Returns:
        Formatted correction prompt to append to agent input

    """
    issues_list = "\n".join(f"- {issue}" for issue in issues)
    hints_list = "\n".join(f"- {hint}" for hint in correction_hints)

    if compact:
        # Use compact format for token efficiency
        return CORRECTION_PROMPT_COMPACT.format(
            attempt_number=attempt_number,
            issues_list="; ".join(issues),
            correction_hints="; ".join(correction_hints),
        )

    return CORRECTION_PROMPT_TEMPLATE.format(
        attempt_number=attempt_number,
        issues_list=issues_list,
        correction_hints=hints_list,
    )


def build_correction_context(
    original_output: dict[str, Any],
    issues: list[str],
    agent_type: str,
) -> dict[str, Any]:
    """Build context dict for correction tracking.

    Args:
        original_output: The output that failed validation
        issues: List of validation issues
        agent_type: Type of agent being corrected

    Returns:
        Context dictionary for logging/observability

    """
    return {
        "agent_type": agent_type,
        "issues_count": len(issues),
        "issues": issues[:5],  # First 5 issues max
        "output_keys": list(original_output.keys()) if original_output else [],
        "correction_triggered": True,
    }


# Agent-specific correction templates for special cases
AGENT_CORRECTION_TEMPLATES: dict[str, str] = {
    "key_insights": """
Focus on:
1. Extract {min_count}+ unique insights from the content
2. Each insight needs a specific title (not generic)
3. Each description must explain WHY this insight matters
4. Reference actual content (quotes, examples, data points)
""",
    "security_auditor": """
Security-specific guidance:
1. Use exact severity levels: low, medium, high, critical
2. Each risk needs a SPECIFIC mitigation (not "review code")
3. Reference OWASP categories or CVE patterns where applicable
4. Avoid vague advice - be actionable
""",
    "tech_comparator": """
Comparison guidance:
1. Name specific technologies (not "the framework")
2. Each comparison entry needs pros AND cons
3. Provide concrete use cases for each technology
4. Include version numbers where relevant
""",
}


def get_agent_specific_guidance(agent_type: str, context: dict[str, Any] | None = None) -> str:
    """Get agent-specific correction guidance if available.

    Args:
        agent_type: Type of agent
        context: Optional context for template variables

    Returns:
        Agent-specific guidance string, or empty string if none

    """
    template = AGENT_CORRECTION_TEMPLATES.get(agent_type, "")
    if template and context:
        try:
            return template.format(**context)
        except KeyError:
            # Template has variables we don't have - return as-is
            return template
    return template
