"""Prompt building utilities for workflow tasks.

All prompt builders are pure functions for easy testing.

Issue #303: Triple-Consumer Output Enhancement
"""


def build_synthesis_user_prompt(formatted_findings: str) -> str:
    """Build user prompt for LLM synthesis with triple-consumer focus.

    Args:
        formatted_findings: Pre-formatted agent findings string

    Returns:
        Formatted user prompt string for synthesis

    Note:
        Issue #303: Enhanced to request all triple-consumer output fields.

    """
    return f"""Analyze and synthesize the following agent findings into a TRIPLE-PURPOSE artifact:

{formatted_findings}

=== GENERATE ALL REQUIRED SECTIONS ===

**REQUIRED - Basic Synthesis:**
□ executive_summary (2-3 sentences)
□ key_findings (3-7 bullet points)
□ synthesis.technical_analysis
□ synthesis.implementation_guidance
□ synthesis.risk_assessment
□ synthesis.recommendations

**REQUIRED - For AI Coding Assistants (ai_assistant_prompt):**
□ context (architectural background)
□ implementation_steps (5-10 ordered steps)
□ code_snippets (dict of purpose→runnable code)
□ file_structure (dict of path→responsibility)
□ success_criteria (3-7 testable outcomes)

**REQUIRED - For Tutor System:**
□ core_concepts (3-7 with definition, why_it_matters, complexity_level)
□ exercises (2-4 hands-on tasks with hints and solutions)
□ self_assessment.quiz_questions (5-10 multiple choice)
□ self_assessment.mastery_checklist (5-10 skills to demonstrate)

**REQUIRED - For Human Readers:**
□ tldr.summary + key_takeaways + time_to_implement
□ diagrams (1-3 Mermaid diagrams with VALID syntax)
□ glossary (5-10 terms with definitions)

**QUALITY CHECKLIST:**
- All code snippets must be complete and runnable
- All Mermaid diagrams must have valid syntax
- Exercise hints should guide without spoiling
- Quiz explanations should teach, not just validate

Generate the complete artifact now.
"""
