"""Dependency mapping agent schemas."""

from typing import Literal

from pydantic import BaseModel, Field


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


class DependencyMapping(BaseModel):
    """Dependency mapping analysis output schema."""

    required_dependencies: list[Dependency] = Field(
        description="Required dependencies for the implementation",
        default_factory=list,
    )
    optional_dependencies: list[Dependency] = Field(
        description="Optional dependencies that enhance functionality",
        default_factory=list,
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
