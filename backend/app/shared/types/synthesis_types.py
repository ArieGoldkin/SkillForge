"""Synthesis-related type definitions.

This module defines TypedDict structures for synthesis workflow metadata
and results.
"""

from typing import TypedDict


class SynthesisMetadata(TypedDict, total=False):
    """Metadata from multi-phase synthesis execution.

    Tracks which phases succeeded and synthesis method used.

    Attributes:
        synthesis_method: Method used ("multi_phase_parallel" or "fallback")
        phase0_compressed_count: Number of compressed findings
        phase1_core_success: Whether core synthesis succeeded
        phase2_learning_success: Whether learning phase succeeded
        phase3_docs_success: Whether docs phase succeeded
        memories_stored: Number of memories stored after synthesis
        synthesis_status: Overall status ("success", "partial", "failed")

    """

    synthesis_method: str
    phase0_compressed_count: int
    phase1_core_success: bool
    phase2_learning_success: bool
    phase3_docs_success: bool
    memories_stored: int
    synthesis_status: str


class CompressedFinding(TypedDict, total=False):
    """Compressed agent finding from Phase 0.

    Attributes:
        agent_name: Name of the source agent
        agent_type: Type of agent
        summary: Compressed summary of finding
        key_points: List of key points
        confidence: Confidence score (0.0-1.0)

    """

    agent_name: str
    agent_type: str
    summary: str
    key_points: list[str]
    confidence: float


class CoreSynthesisResult(TypedDict, total=False):
    """Result from Phase 1 core synthesis.

    Attributes:
        executive_summary: High-level summary
        key_findings: List of key findings
        synthesis: Detailed synthesis text
        conflicts_resolved: Resolved conflicts
        coverage_gaps: Identified gaps

    """

    executive_summary: str
    key_findings: list[str]
    synthesis: str
    conflicts_resolved: list[str]
    coverage_gaps: list[str]


class LearningSynthesisResult(TypedDict, total=False):
    """Result from Phase 2 learning synthesis.

    Attributes:
        core_concepts: List of concepts with descriptions
        exercises: Practice exercises
        self_assessment: Self-assessment questions

    """

    core_concepts: list[dict[str, str]]
    exercises: list[str]
    self_assessment: list[str]


class DocsSynthesisResult(TypedDict, total=False):
    """Result from Phase 3 docs synthesis.

    Attributes:
        tldr: Short summary
        ai_assistant_prompt: Prompt for AI assistant
        diagrams: Mermaid diagrams
        glossary: Term definitions

    """

    tldr: str
    ai_assistant_prompt: str
    diagrams: list[str]
    glossary: dict[str, str]

