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

CORE_SYNTHESIS_PROMPT = """You are synthesizing technical analysis findings into an
executive summary.

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
- synthesis (object with technical_analysis, implementation_guidance, risk_assessment,
  recommendations)
- conflicts_resolved (list of objects)
- coverage_gaps (list of objects)
- coverage_score (float 0.0-1.0)
"""


# ============================================================================
# PHASE 2: LEARNING SYNTHESIS (~1K tokens)
# ============================================================================

LEARNING_SYNTHESIS_PROMPT = """You are creating educational content from technical analysis.

## Your Task
Generate tutor-ready learning materials for the LearningSynthesisSchema.

### 1. Core Concepts (core_concepts) - List of 3-7 objects
Each concept object must have these EXACT fields:
- name: String 2-100 chars, concept name (e.g., "Semantic Chunking")
- definition: String 50-500 chars, clear 2-3 sentence definition
- why_it_matters: String 30-300 chars, practical importance
- complexity_level: String, MUST be one of: "Beginner", "Intermediate", "Advanced", "Expert"
- related_concepts: List of 0-5 strings, connected concept names

### 2. Exercises (exercises) - List of 2-4 objects
Each exercise object must have these EXACT fields:
- title: String 5-100 chars, action-oriented name (e.g., "Build a Semantic Search API")
- difficulty: String, MUST be one of: "Beginner", "Intermediate", "Advanced", "Expert"
- description: String 50-1000 chars, what to build and why
- hints: List of 3-5 progressive hints (strings), guide without spoiling
- solution: String (can be empty), complete working solution with comments
- learning_objectives: List of 2-5 strings, skills this exercise reinforces

### 3. Self Assessment (self_assessment) - Single object with:
- quiz_questions: List of 5-10 question objects, each with:
    * question: String 10-300 chars, clear question testing a concept
    * options: List of 2-5 answer choices (strings)
    * correct_answer: String, MUST EXACTLY match one of the options
    * explanation: String 30-500 chars, why this answer is correct
- mastery_checklist: List of 5-10 "I can..." statements (strings)

## CRITICAL FIELD VALUE CONSTRAINTS
- complexity_level and difficulty MUST be exactly: "Beginner", "Intermediate",
  "Advanced", or "Expert"."
- NOT: "beginner", "easy", "medium", "hard", "simple", "1", "2", etc.
- correct_answer MUST exactly match one option or validation fails

## PEDAGOGICAL PRINCIPLES
- **Scaffolding**: Build on previous concepts (order Beginner → Expert)
- **Active Learning**: Exercises require hands-on practice
- **Metacognition**: Self-assessment helps learners track progress
- **Socratic Method**: Hints guide discovery rather than providing answers

## Agent Findings Summary:
{agent_findings}

## CRITICAL OUTPUT FORMAT
Return VALID JSON matching LearningSynthesisSchema EXACTLY:
```json
{{
  "core_concepts": [...3-7 concept objects...],
  "exercises": [...2-4 exercise objects...],
  "self_assessment": {{
    "quiz_questions": [...5-10 question objects...],
    "mastery_checklist": [...5-10 strings...]
  }}
}}
```
Field names, counts, and string patterns must match EXACTLY or validation will fail.
"""


# ============================================================================
# PHASE 3: DOCS SYNTHESIS (~1K tokens)
# ============================================================================

DOCS_SYNTHESIS_PROMPT = """You are creating documentation for developers and AI assistants.

## Your Task
Generate developer-friendly documentation for the DocsSynthesisSchema.

### PART 1: Quick Reference (quick_reference)
Generate an object with these EXACT fields:
- primary_technology: String "TechName version" (e.g., "LangGraph 0.6.7 + PostgreSQL 14")
- complexity: String "Level (Est. X-Y hours)" (e.g., "Intermediate (Est. 3-4 hours)")
- prerequisites: List of 0-4 strings (e.g., ["Python 3.11+", "Docker installed"])
- critical_commands: List of 0-6 copy-paste commands (e.g., ["pip install langgraph==0.6.7"])
- files_to_modify: List of 0-10 file paths with purpose
- files_disclaimer: String (use default: "⚠️ AI-suggested structure based on content patterns")
- gotchas: List of 0-5 objects, each with:
    * issue: String - the pitfall description
    * symptom: String - what you'll see when this happens
    * quick_fix: String - how to fix it

### PART 2: TL;DR Section (tldr)
Generate an object with these EXACT fields:
- summary: String 50-500 chars, 2-3 sentences overview
- key_takeaways: List of 3-5 concrete outcomes (strings)
- time_to_implement: String "Total time (breakdown)" (e.g., "4-6 hours (2h setup, 2h impl)")

### PART 3: AI Assistant Prompt (ai_assistant_prompt)
Pre-formatted context for AI coding assistants with these EXACT fields:
- context: String 50-1000 chars, architectural background
- implementation_steps: List of 5-10 ordered imperative commands (strings)
- code_snippets: Dict of purpose→complete runnable code (max 5 keys)
- file_structure: Dict of file_path→responsibility description
- success_criteria: List of 3-7 testable outcomes (strings)

### PART 4: Diagrams (diagrams)
Generate a list of 1-3 Mermaid diagram objects, each with these EXACT fields:
- title: String 5-100 chars, diagram name
- type: String, one of: "flowchart", "sequence", "class", "state", "er", "gantt"
- mermaid_code: String, valid Mermaid.js syntax (NOT "content"!)
- description: String 30-500 chars, what the diagram shows

**CRITICAL DIAGRAM CONSTRAINTS** (prevents rendering issues):
- Diamond nodes {{label}}: MAX 5 chars (use {{OK?}}, {{Yes}}, {{No}} - NOT {{Valid?}})
- Rectangle nodes [label]: Split long text, max 15 chars/word
- Terminal nodes: Keep concise ([Done], [End], [Error])

### PART 5: Glossary (glossary)
Generate a list of 5-10 term objects, each with these EXACT fields:
- term: String 1-100 chars, the technical term or acronym
- definition: String 20-500 chars, clear definition
- see_also: List of 0-5 related term names (strings)

## DOCUMENTATION QUALITY REQUIREMENTS
1. **Actionable**: Every section enables immediate action
2. **Specific**: Include versions, paths, commands - no vague guidance
3. **Complete**: Code snippets must be runnable, diagrams must render
4. **Scannable**: TL;DR readable in 10 seconds, full docs in 5 minutes

## Agent Findings Summary:
{agent_findings}

## CRITICAL OUTPUT FORMAT
Return VALID JSON matching DocsSynthesisSchema EXACTLY:
```json
{{
  "quick_reference": {{...exact fields above...}},
  "tldr": {{...exact fields above...}},
  "ai_assistant_prompt": {{...exact fields above...}},
  "diagrams": [...1-3 diagram objects with mermaid_code NOT content...],
  "glossary": [...5-10 term objects...]
}}
```
Field names and structures must match EXACTLY or validation will fail.
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
            parts.append(f"  - {insight}")  # noqa: PERF401

        if f.get("critical_warnings"):
            parts.append("⚠️ Warnings:")
            for warning in f["critical_warnings"]:
                parts.append(f"  - {warning}")  # noqa: PERF401

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
