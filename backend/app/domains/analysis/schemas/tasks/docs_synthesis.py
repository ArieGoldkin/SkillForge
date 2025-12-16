"""Phase 3: Documentation Synthesis Schema - OPTIONAL reference materials.

This schema defines reference content for AI assistants and human readers:
quick reference cards, TLDR sections, AI assistant prompts, visual diagrams,
and glossary terms.

Generated in parallel with Phase 1 (core) and Phase 2 (learning). Always included
for technical content, but may be skipped for brief or non-technical materials.

Related: Issue #302 - Triple-Purpose Schema Enhancement
Related: Issue #299-304 - Artifact Quality Initiative
"""

from pydantic import BaseModel, Field, field_validator

from app.domains.analysis.schemas.tasks.aggregated_insights import (
    AIAssistantPrompt,
    GlossaryTerm,
    MermaidDiagram,
    QuickReference,
    TLDRSection,
)


class DocsSynthesisSchema(BaseModel):
    """Phase 3: Documentation and reference materials - generated in parallel.

    Contains content optimized for quick reference and AI assistant context:
    - Quick reference card with critical commands and gotchas
    - TLDR section for 10-30 second human scanning
    - AI assistant prompt with implementation steps and code snippets
    - Mermaid diagrams for visual explanation (flowcharts, sequences, architecture)
    - Glossary terms with cross-references for knowledge graph

    This phase is OPTIONAL but typically included for technical content.
    When generated, it completes in ~15-20s parallel to Phase 1.

    Examples of when to SKIP this phase:
    - Very brief content (<500 words) without implementation details
    - Content without actionable commands or code
    - Non-technical blog posts or announcements

    Examples of when to INCLUDE this phase:
    - Technical documentation with setup instructions
    - Tutorials with code examples
    - Architecture guides with system diagrams
    - API documentation
    - Research papers with technical concepts
    """

    quick_reference: QuickReference = Field(
        description=(
            "Front-loaded critical information for fast scanning. "
            "Includes: primary_technology (with versions), complexity (with time estimate), "
            "prerequisites (max 4), critical_commands (max 6), files_to_modify (max 10), "
            "files_disclaimer, gotchas (max 5 with symptom + quick_fix). "
            "Designed for 10-15 second scanning per research findings."
        )
    )

    tldr: TLDRSection = Field(
        description=(
            "Executive summary optimized for human scanning (10-30 seconds). "
            "Includes: summary (2-3 sentences), key_takeaways (3-5 items), "
            "time_to_implement (with breakdown). "
            "Provides immediate value assessment for busy developers."
        )
    )

    ai_assistant_prompt: AIAssistantPrompt = Field(
        description=(
            "Pre-formatted context for AI coding assistants (Claude, Cursor, Copilot). "
            "Includes: context (architectural background), implementation_steps (5-10 ordered steps), "
            "code_snippets (max 5 by purpose), file_structure (with purpose annotations), "
            "success_criteria (3-7 testable outcomes). "
            "Optimized for one-shot code generation with high accuracy."
        )
    )

    diagrams: list[MermaidDiagram] = Field(
        description=(
            "Mermaid.js diagrams for visual explanation. "
            "Each diagram includes: title, type (flowchart/sequence/class/state/er/gantt), "
            "mermaid_code (syntactically valid), description (2-3 sentences). "
            "Must have 1-3 diagrams covering key workflows or architecture. "
            "CRITICAL: Follow node label constraints to prevent text truncation: "
            "- Diamond nodes {label}: MAX 5 chars (e.g., {OK?}, {Yes}, {No}) "
            "- Rectangle nodes [label]: MAX 15 chars per word, split long text"
        ),
        min_length=1,
        max_length=3,
    )

    glossary: list[GlossaryTerm] = Field(
        description=(
            "Technical term definitions with cross-references. "
            "Each term includes: term (name/acronym), definition (1-2 sentences), "
            "see_also (max 5 related terms). "
            "Must have 5-10 terms for comprehensive knowledge base. "
            "Prioritize domain-specific jargon and acronyms."
        ),
        min_length=5,
        max_length=10,
    )

    @field_validator("diagrams")
    @classmethod
    def validate_diagrams_count(cls, v: list[MermaidDiagram]) -> list[MermaidDiagram]:
        """Ensure diagrams has 1-3 items."""
        if not 1 <= len(v) <= 3:
            msg = f"diagrams must have 1-3 items, got {len(v)}"
            raise ValueError(msg)
        return v

    @field_validator("glossary")
    @classmethod
    def validate_glossary_count(cls, v: list[GlossaryTerm]) -> list[GlossaryTerm]:
        """Ensure glossary has 5-10 items."""
        if not 5 <= len(v) <= 10:
            msg = f"glossary must have 5-10 items, got {len(v)}"
            raise ValueError(msg)
        return v

    @field_validator("diagrams")
    @classmethod
    def validate_diagram_types(cls, v: list[MermaidDiagram]) -> list[MermaidDiagram]:
        """Validate that diagram types are valid."""
        valid_types = {"flowchart", "sequence", "class", "state", "er", "gantt"}
        for diagram in v:
            if diagram.type not in valid_types:
                msg = (
                    f"diagram '{diagram.title}' has invalid type "
                    f"'{diagram.type}'. Must be one of: {valid_types}"
                )
                raise ValueError(msg)
        return v

    @field_validator("quick_reference")
    @classmethod
    def validate_quick_reference_lengths(cls, v: QuickReference) -> QuickReference:
        """Validate that quick_reference list fields don't exceed max lengths."""
        if len(v.prerequisites) > 4:
            msg = f"prerequisites must have max 4 items, got {len(v.prerequisites)}"
            raise ValueError(msg)
        if len(v.critical_commands) > 6:
            msg = f"critical_commands must have max 6 items, got {len(v.critical_commands)}"
            raise ValueError(msg)
        if len(v.files_to_modify) > 10:
            msg = f"files_to_modify must have max 10 items, got {len(v.files_to_modify)}"
            raise ValueError(msg)
        if len(v.gotchas) > 5:
            msg = f"gotchas must have max 5 items, got {len(v.gotchas)}"
            raise ValueError(msg)
        return v

    @field_validator("tldr")
    @classmethod
    def validate_tldr_key_takeaways(cls, v: TLDRSection) -> TLDRSection:
        """Validate that TLDR key_takeaways has 3-5 items."""
        if not 3 <= len(v.key_takeaways) <= 5:
            msg = f"tldr.key_takeaways must have 3-5 items, got {len(v.key_takeaways)}"
            raise ValueError(msg)
        return v

    @field_validator("ai_assistant_prompt")
    @classmethod
    def validate_ai_assistant_prompt_lengths(cls, v: AIAssistantPrompt) -> AIAssistantPrompt:
        """Validate that ai_assistant_prompt list fields have correct lengths."""
        if not 5 <= len(v.implementation_steps) <= 10:
            msg = (
                f"ai_assistant_prompt.implementation_steps must have 5-10 items, "
                f"got {len(v.implementation_steps)}"
            )
            raise ValueError(msg)
        if len(v.code_snippets) > 5:
            msg = (
                f"ai_assistant_prompt.code_snippets must have max 5 items, "
                f"got {len(v.code_snippets)}"
            )
            raise ValueError(msg)
        if not 3 <= len(v.success_criteria) <= 7:
            msg = (
                f"ai_assistant_prompt.success_criteria must have 3-7 items, "
                f"got {len(v.success_criteria)}"
            )
            raise ValueError(msg)
        return v
