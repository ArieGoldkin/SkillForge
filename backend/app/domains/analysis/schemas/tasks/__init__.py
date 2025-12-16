"""Task output schemas for analysis domain.

These schemas define the structured outputs from analysis workflow tasks.
"""

# Re-export all task schemas for convenience
from app.domains.analysis.schemas.tasks.aggregated_insights import (
    AggregatedInsights,
    ConflictResolution,
    CoverageGap,
    CrossDomainConnection,
    GotchaItem,
    QuickReference,
    Synthesis,
)
from app.domains.analysis.schemas.tasks.core_synthesis import CoreSynthesisSchema
from app.domains.analysis.schemas.tasks.docs_synthesis import DocsSynthesisSchema
from app.domains.analysis.schemas.tasks.learning_synthesis import LearningSynthesisSchema

__all__ = [
    "AggregatedInsights",
    "ConflictResolution",
    "CoreSynthesisSchema",
    "CoverageGap",
    "CrossDomainConnection",
    "DocsSynthesisSchema",
    "GotchaItem",
    "LearningSynthesisSchema",
    "QuickReference",
    "Synthesis",
]
