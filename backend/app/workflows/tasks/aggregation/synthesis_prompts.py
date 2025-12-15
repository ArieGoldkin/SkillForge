"""Phase-specific synthesis prompts for multi-phase artifact generation.

Each prompt is focused on a specific output schema, reducing token usage
and improving generation reliability.

Issue #299-304: Replaces monolithic 4K token SYNTHESIS_SYSTEM_PROMPT
with three ~1K token prompts, each targeting a specific synthesis phase.
"""

from typing import Any

# ============================================================================
# PHASE 1: CORE SYNTHESIS (~1K tokens)
# ============================================================================

CORE_SYNTHESIS_PROMPT = """You are synthesizing technical analysis findings into an executive summary.

## Your Task
Generate a concise synthesis of the agent findings with:

1. **Executive Summary** (2-3 sentences): What is this content about and why does it matter?

2. **Key Findings** (3-7 bullets): The most important insights from all agents

3. **Synthesis** sections:
   - technical_analysis: Technical details and architecture insights
   - implementation_guidance: How to implement this
   - risk_assessment: Potential risks and mitigations
   - recommendations: Actionable next steps

4. **Conflicts Resolved**: Any disagreements between agents and how you resolved them

5. **Coverage Gaps**: What's missing from the analysis

6. **Coverage Score** (0.0-1.0): How complete is this analysis?

## Guidelines
- Be concise but comprehensive
- Prioritize actionable insights over theoretical discussion
- Highlight security concerns prominently
- Include specific code references where relevant

## AGENTS PROVIDED (8 specialized analysts):
1. Tech Comparator - Technology comparisons and alternatives
2. Security Auditor - Security risks and best practices
3. Implementation Planner - Step-by-step implementation guidance
4. Integration Feasibility - Integration with modern stacks
5. Performance Analyst - Performance trade-offs and optimization
6. Code Quality Critic - Best practices and antipatterns
7. Trend Validator - Technology trend alignment (2025+)
8. Dependency Mapper - Required libraries and dependencies

## CONFIDENCE HANDLING
Each agent provides confidence_score (0.0-1.0). When agents disagree:
- Prioritize higher confidence scores
- Document conflicts in conflicts_resolved with reasoning

## COVERAGE ACKNOWLEDGMENT
Each agent reports `data_availability` (sufficient/limited/insufficient):
- "sufficient": Agent had full data - trust findings completely
- "limited": Agent had partial data - acknowledge gaps in coverage_gaps
- "insufficient": Agent found minimal data - mark as coverage gap

When multiple agents report "limited" or "insufficient", or coverage_score < 0.5,
acknowledge gaps in executive_summary. Example: "Note: This analysis is based on
conceptual content without code examples, so implementation guidance is inferred
rather than extracted."

This enables HONEST synthesis - don't hallucinate details that weren't in the content.
It's better to say "No security patterns detected" than to fabricate risks.

## CRITICAL MARKDOWN FORMATTING RULES
1. **Paragraph Separation**: Use TWO newlines (blank line) between paragraphs
2. **Section Headers**: When using bold headers like **Title:**, put content on new line:
   CORRECT:
   **Immediate Actions:**
   Start with implementation...

   WRONG:
   **Immediate Actions:** Start with implementation...

3. **List Items**: Use proper markdown bullets with space after dash:
   - Item one
   - Item two

4. **Code Blocks**: Always specify language after triple backticks

## Agent Findings:
{agent_findings}

## Conflicts to Resolve:
{conflicts}

## Output Format:
Return valid JSON matching the CoreSynthesisSchema with fields:
- executive_summary (string)
- key_findings (list of strings)
- synthesis (object with technical_analysis, implementation_guidance, risk_assessment, recommendations)
- conflicts_resolved (list of objects)
- coverage_gaps (list of objects)
- coverage_score (float 0.0-1.0)
"""


# ============================================================================
# PHASE 2: LEARNING SYNTHESIS (~1K tokens)
# ============================================================================

LEARNING_SYNTHESIS_PROMPT = """You are creating educational content from technical analysis.

## Your Task
Generate tutor-ready learning materials for a Socratic learning system:

1. **Core Concepts** (3-7 items):
   - name: Concept name
   - definition: Clear 2-3 sentence definition
   - why_it_matters: Practical importance
   - complexity_level: beginner/intermediate/advanced
   - related_concepts: Connected ideas (list of strings)

2. **Exercises** (2-4 items):
   - title: Exercise name
   - difficulty: easy/medium/hard
   - description: What to do (clear task description)
   - hints: Help without giving away the answer (list of 2-4 hints)
   - learning_objectives: What skills this builds (list of strings)
   - solution: Complete solution (hidden from learner initially)

3. **Self Assessment**:
   - quiz_questions: 5-10 multiple choice questions, each with:
     * question: The question text
     * options: List of 3-4 answer choices
     * correct_answer: The correct option text
     * explanation: Why this is correct and others aren't
   - mastery_checklist: 5-10 "I can..." statements

## Guidelines
- Use analogies to explain complex concepts
- Order concepts from simple to complex (beginner → intermediate → advanced)
- Make exercises practical, not theoretical
- Quiz questions should test understanding, not memorization
- Difficulty progression: start easy, build to harder challenges
- Learning objectives should be measurable and specific

## PEDAGOGICAL PRINCIPLES
- **Scaffolding**: Build on previous concepts
- **Active Learning**: Exercises require hands-on practice
- **Metacognition**: Self-assessment helps learners track progress
- **Socratic Method**: Hints guide discovery rather than providing answers

## Agent Findings Summary:
{agent_findings}

## Output Format:
Return valid JSON matching the LearningSynthesisSchema with fields:
- core_concepts (list of objects)
- exercises (list of objects)
- self_assessment (object with quiz_questions and mastery_checklist)
"""


# ============================================================================
# PHASE 3: DOCS SYNTHESIS (~1K tokens)
# ============================================================================

DOCS_SYNTHESIS_PROMPT = """You are creating documentation for developers and AI assistants.

## Your Task
Generate developer-friendly documentation in THREE parts:

### PART 1: Quick Reference
- primary_technology: Main tech discussed
- complexity: 1-5 scale (1=beginner, 5=expert)
- prerequisites: What you need to know first (list of strings)
- key_commands: Important CLI commands (list of strings)
- common_pitfalls: What to avoid (list of strings)
- debugging_tips: How to fix common issues (list of strings)

### PART 2: TL;DR Section
- one_liner: 20-word summary
- use_when: When to use this
- skip_when: When NOT to use this
- key_takeaways: 3-5 bullet points
- time_to_implement: Estimated hours/days

### PART 3: AI Assistant Prompt
Pre-formatted prompt that enables AI coding assistants (Claude, Cursor, Copilot, Windsurf)
to generate accurate code on first attempt:
- context: What an AI assistant needs to know (architectural background)
- implementation_steps: 5-10 ordered, imperative commands
- code_snippets: Dict of purpose→complete runnable code (max 5 snippets)
- file_structure: Dict of file_path→responsibility
- success_criteria: 3-7 testable outcomes

### PART 4: Diagrams (1-3 Mermaid diagrams)
- title: Diagram name
- type: flowchart/sequence/class/er
- content: Valid Mermaid syntax
- description: What the diagram shows

**CRITICAL DIAGRAM CONSTRAINTS** (prevents rendering issues):
- Diamond nodes {label}: MAX 5 chars (use {OK?}, {Yes}, {No} - NOT {Valid?})
- Rectangle nodes [label]: Split long text, max 15 chars/word
- Terminal nodes: Keep concise ([Done], [End], [Error])
- Always test: labels must fit inside shapes without truncation

### PART 5: Glossary (5-10 terms)
- term: Technical term
- definition: Plain English definition
- see_also: Related terms (list of strings)

## Guidelines
- Mermaid diagrams MUST use valid syntax (test before outputting)
- AI prompt should work with ANY coding assistant (Claude, Cursor, Copilot, etc.)
- Quick reference should fit on one screen
- Glossary for terms a junior developer might not know
- Code snippets must be complete and runnable with comments
- File structure should show recommended project organization
- Success criteria should be objective and testable

## DOCUMENTATION QUALITY
1. **Actionable**: Every section enables immediate action
2. **Specific**: Include versions, paths, commands - no vague guidance
3. **Complete**: Code snippets must be runnable, diagrams must render
4. **Scannable**: TL;DR readable in 10 seconds, full docs in 5 minutes

## Agent Findings Summary:
{agent_findings}

## Output Format:
Return valid JSON matching the DocsSynthesisSchema with fields:
- quick_reference (object)
- tldr (object)
- ai_assistant_prompt (object)
- diagrams (list of objects)
- glossary (list of objects)
"""


# ============================================================================
# PROMPT BUILDER FUNCTIONS
# ============================================================================


def build_core_prompt(
    compressed_findings: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    """Build the Phase 1 (Core) synthesis prompt.

    Args:
        compressed_findings: Compressed agent findings with key insights
        conflicts: Detected conflicts between agents

    Returns:
        Formatted prompt string with findings and conflicts inserted

    """
    findings_text = _format_compressed_findings(compressed_findings)
    conflicts_text = _format_conflicts(conflicts)
    return CORE_SYNTHESIS_PROMPT.format(
        agent_findings=findings_text,
        conflicts=conflicts_text,
    )


def build_learning_prompt(compressed_findings: list[dict[str, Any]]) -> str:
    """Build the Phase 2 (Learning) synthesis prompt.

    Args:
        compressed_findings: Compressed agent findings with key insights

    Returns:
        Formatted prompt string with findings inserted

    """
    findings_text = _format_compressed_findings(compressed_findings)
    return LEARNING_SYNTHESIS_PROMPT.format(agent_findings=findings_text)


def build_docs_prompt(compressed_findings: list[dict[str, Any]]) -> str:
    """Build the Phase 3 (Docs) synthesis prompt.

    Args:
        compressed_findings: Compressed agent findings with key insights

    Returns:
        Formatted prompt string with findings inserted

    """
    findings_text = _format_compressed_findings(compressed_findings)
    return DOCS_SYNTHESIS_PROMPT.format(agent_findings=findings_text)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _format_compressed_findings(findings: list[dict[str, Any]]) -> str:
    """Format compressed findings for prompt insertion.

    Args:
        findings: List of compressed agent findings

    Returns:
        Formatted multi-line string suitable for prompt insertion

    """
    parts = []
    for f in findings:
        parts.append(f"### {f.get('agent_name', 'Unknown Agent')}")
        parts.append(f"Confidence: {f.get('confidence', 'N/A')}")

        # Data availability (Issue #299-304)
        if f.get("data_availability"):
            parts.append(f"Data Availability: {f['data_availability']}")
            if f.get("data_availability_note"):
                parts.append(f"Note: {f['data_availability_note']}")

        parts.append("Key Insights:")
        for insight in f.get("key_insights", []):
            parts.append(f"  - {insight}")

        if f.get("critical_warnings"):
            parts.append("⚠️ Warnings:")
            for warning in f["critical_warnings"]:
                parts.append(f"  - {warning}")

        parts.append("")  # Blank line between agents

    return "\n".join(parts)


def _format_conflicts(conflicts: list[dict[str, Any]]) -> str:
    """Format conflicts for prompt insertion.

    Args:
        conflicts: List of detected conflicts

    Returns:
        Formatted multi-line string suitable for prompt insertion

    """
    if not conflicts:
        return "No conflicts detected."

    parts = []
    for c in conflicts:
        description = c.get("description", str(c))
        parts.append(f"- {description}")

    return "\n".join(parts)
