"""Schemas for workflow tasks."""

from app.workflows.tasks.schemas.aggregated_insights import (
    AggregatedInsights,
    ConflictResolution,
    Synthesis,
)
from app.workflows.tasks.schemas.core_synthesis import CoreSynthesisSchema
from app.workflows.tasks.schemas.docs_synthesis import DocsSynthesisSchema
from app.workflows.tasks.schemas.learning_synthesis import LearningSynthesisSchema

__all__ = [
    "AggregatedInsights",
    "ConflictResolution",
    "CoreSynthesisSchema",
    "DocsSynthesisSchema",
    "LearningSynthesisSchema",
    "Synthesis",
]
