"""Base schemas for agent structured outputs.

This module provides base classes and mixins for agent response schemas.
All specialized agent schemas should inherit from or include these base types.

Issue #299-304: Graceful degradation - agents report data availability.
"""

from typing import Literal

from pydantic import BaseModel, Field


class DataAvailabilityMixin(BaseModel):
    """Mixin for agents to report data availability.

    Issue #299-304: Agents should honestly report whether they found
    sufficient data for their analysis type, rather than "failing"
    or producing low-quality output.

    This enables:
    1. Synthesis to acknowledge coverage gaps transparently
    2. Quality gate to evaluate based on what was possible
    3. Artifacts to indicate which sections have full vs partial analysis

    """

    data_availability: Literal["sufficient", "limited", "insufficient"] = Field(
        description=(
            "Report how much relevant data you found for this analysis type:\n"
            "- 'sufficient': Found all data needed for thorough analysis\n"
            "- 'limited': Found some relevant data, analysis is partial but valuable\n"
            "- 'insufficient': Found minimal relevant data for this analysis type\n\n"
            "Be honest - reporting 'limited' or 'insufficient' is better than "
            "hallucinating details. This helps users understand coverage gaps."
        ),
        default="sufficient",
    )
    data_availability_note: str = Field(
        description=(
            "Brief note explaining data availability. Required when data_availability "
            "is 'limited' or 'insufficient'. Examples:\n"
            "- 'No code examples found in content'\n"
            "- 'Only high-level architecture discussed, no implementation details'\n"
            "- 'Performance metrics mentioned but no benchmarks provided'"
        ),
        default="",
    )


# Type alias for use in agent output schemas
DataAvailabilityLevel = Literal["sufficient", "limited", "insufficient"]
