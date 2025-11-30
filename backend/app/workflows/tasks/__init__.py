"""Workflow task functions for content analysis.

This module exports all workflow tasks for use in the analysis workflow.
"""

# execute_agents removed - agents now execute as individual nodes via Send API
from app.workflows.tasks.aggregate_findings import aggregate_findings
from app.workflows.tasks.extract_content import extract_content
from app.workflows.tasks.generate_artifact import generate_artifact
from app.workflows.tasks.generate_embedding import generate_embedding

__all__ = [
    "aggregate_findings",
    "extract_content",
    "generate_artifact",
    "generate_embedding",
]
