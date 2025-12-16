"""Workflow task functions for content analysis.

This module exports all workflow tasks for use in the analysis workflow.
"""

# execute_agents removed - agents now execute as individual nodes via Send API
from app.domains.analysis.workflows.tasks.aggregate_findings import aggregate_findings
from app.domains.analysis.workflows.tasks.chunk_content import chunk_content
from app.domains.analysis.workflows.tasks.extract_content import extract_content
from app.domains.analysis.workflows.tasks.generate_artifact import generate_artifact
from app.domains.analysis.workflows.tasks.generate_embedding import generate_embedding, generate_embeddings_batch
from app.domains.analysis.workflows.tasks.store_embeddings import store_embeddings
from app.domains.analysis.workflows.tasks.telemetry import log_chunking_metrics

__all__ = [
    "aggregate_findings",
    "chunk_content",
    "extract_content",
    "generate_artifact",
    "generate_embedding",
    "generate_embeddings_batch",
    "log_chunking_metrics",
    "store_embeddings",
]
