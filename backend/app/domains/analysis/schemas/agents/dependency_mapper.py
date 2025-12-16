"""Dependency mapping agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domains.analysis.schemas.agents.base import DataAvailabilityMixin


class Dependency(BaseModel):
    """Dependency information."""

    name: str = Field(description="Dependency name (package, library, framework)")
    version: str = Field(description="Version or version range (e.g., '^1.0.0', '>=2.0.0')")
    purpose: str = Field(
        description=("Single sentence describing the purpose of this dependency in the project.")
    )
    compatibility: Literal["compatible", "incompatible", "unknown"] = Field(
        description="Compatibility status with other dependencies"
    )


class DependencyMapping(DataAvailabilityMixin):
    """Dependency mapping analysis output schema.

    Issue #299-304: Inherits DataAvailabilityMixin to report data coverage.
    """

    required_dependencies: list[Dependency] = Field(
        description="Required dependencies for the implementation",
        default_factory=list,
    )
    optional_dependencies: list[Dependency] = Field(
        description="Optional dependencies that enhance functionality",
        default_factory=list,
    )
    primary_framework: str | None = Field(
        description="Primary framework identified (e.g., 'fastapi', 'react', 'django')",
        default=None,
    )
    core_dependencies: list[Dependency] = Field(
        description=(
            "Core dependencies required for the primary framework to function. "
            "These are essential dependencies that the framework depends on."
        ),
        default_factory=list,
    )
    optional_dependencies_by_purpose: dict[str, list[Dependency]] = Field(
        description=(
            "Optional dependencies grouped by purpose (e.g., 'database', 'auth', "
            "'validation', 'testing'). Keys are purpose names, values are lists of "
            "dependencies for that purpose."
        ),
        default_factory=dict,
    )
    alternatives: dict[str, list[str]] = Field(
        description=(
            "Alternative libraries for each purpose. Keys are purpose names "
            "(e.g., 'database', 'auth'), values are lists of alternative library names."
        ),
        default_factory=dict,
    )
    version_matrix: dict[str, str] = Field(
        description=(
            "Version compatibility matrix. Keys are dependency names, values are "
            "version constraints (e.g., '>=3.0.0 <4.0.0', '^18.0.0')."
        ),
        default_factory=dict,
    )
    version_conflicts: list[str] = Field(
        description=(
            "Potential version conflicts between dependencies. "
            "Each item should be a single sentence describing the conflict."
        ),
        default_factory=list,
    )
    peer_dependencies: list[str] = Field(
        description=(
            "Peer dependencies or requirements (e.g., Node.js version, Python version). "
            "Each item should be a single concise phrase."
        ),
        default_factory=list,
    )
    installation_notes: list[str] = Field(
        description=(
            "Installation and setup notes for dependencies. "
            "Each item should be a single actionable instruction."
        ),
        default_factory=list,
    )
    recommendation: str = Field(
        description=(
            "Dependency management recommendation. "
            "Write as 2-3 cohesive sentences summarizing the dependency strategy."
        )
    )
    confidence_score: float = Field(
        description=(
            "Confidence score (0.0-1.0) representing both the quality and certainty "
            "of this dependency mapping. Consider: accuracy of dependency identification, "
            "correctness of version compatibility assessment, completeness of conflict "
            "detection, and confidence in installation notes. Higher scores indicate "
            "more accurate and comprehensive dependency mappings."
        ),
        ge=0.0,
        le=1.0,
    )
