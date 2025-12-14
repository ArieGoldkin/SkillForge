"""Content grounding instructions for all agents.

This module provides common grounding instructions that ensure agents
analyze the ACTUAL provided content rather than generating generic responses
or copying examples from prompts.

Issue #ARTIFACT-QUALITY: Added to fix agents ignoring source content.
"""

# Grounding instructions prepended to ALL agent prompts
GROUNDING_INSTRUCTIONS = """
=== CRITICAL: CONTENT GROUNDING REQUIREMENTS ===

**YOUR ANALYSIS MUST BE GROUNDED IN THE PROVIDED CONTENT.**

1. **ONLY analyze what's in the content** - Every claim must reference the source material
2. **If something isn't mentioned, say "Not covered in source"** - NEVER invent data
3. **NEVER fabricate**: CVEs, version numbers, metrics, file paths, or code not in the content
4. **Quote or paraphrase the source** - Show where your analysis comes from
5. **Examples in this prompt are FORMAT ONLY** - Do NOT copy example values

FORBIDDEN:
- Inventing security vulnerabilities or CVE numbers
- Making up version numbers not mentioned in content
- Creating file paths that aren't in the source
- Generating generic advice unrelated to the content
- Copying example values from this prompt

IF THE CONTENT DOESN'T COVER YOUR ANALYSIS AREA:
Return minimal findings with a note: "Source content does not cover [topic]"
Set confidence_score to 0.3 or lower for unsupported analysis.

=== END GROUNDING REQUIREMENTS ===
"""


def apply_grounding(base_prompt: str) -> str:
    """Apply grounding instructions to an agent prompt.

    Args:
        base_prompt: The agent's base system prompt

    Returns:
        Prompt with grounding instructions prepended

    """
    return f"{GROUNDING_INSTRUCTIONS}\n\n{base_prompt}"
