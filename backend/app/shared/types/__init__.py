"""Shared type definitions for SkillForge workflows.

This module provides TypedDict definitions that are shared across
multiple domains (analysis, tutor) to ensure type safety and
consistency in LangGraph state management.

Usage:
    from app.shared.types import AgentFinding, WorkflowMetrics, TutorMessage
"""

from app.shared.types.artifact_types import ArtifactMetadata, ArtifactSection, GeneratedArtifact
from app.shared.types.message_types import TutorMessage
from app.shared.types.synthesis_types import (
    CompressedFinding,
    CoreSynthesisResult,
    DocsSynthesisResult,
    LearningSynthesisResult,
    SynthesisMetadata,
)
from app.shared.types.workflow_types import AgentFinding, WorkflowMetrics

__all__ = [
    "AgentFinding",
    "ArtifactMetadata",
    "ArtifactSection",
    "CompressedFinding",
    "CoreSynthesisResult",
    "DocsSynthesisResult",
    "GeneratedArtifact",
    "LearningSynthesisResult",
    "SynthesisMetadata",
    "TutorMessage",
    "WorkflowMetrics",
]
