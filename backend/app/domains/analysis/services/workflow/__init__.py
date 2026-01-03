"""Workflow orchestration services for analysis domain.

This package contains services for:
- Workflow execution and orchestration
- Workflow result validation
- Exception handling for workflows
- Error aggregation for workflow-level failure detection (Issue #627, #628)
"""

from app.domains.analysis.services.workflow.error_aggregator import (
    WorkflowErrorAggregator,
    workflow_error_aggregator,
)
from app.domains.analysis.services.workflow.exception_handler import (
    handle_workflow_exception,
)
from app.domains.analysis.services.workflow.orchestrator import WorkflowOrchestrator

__all__ = [
    "WorkflowErrorAggregator",
    "WorkflowOrchestrator",
    "handle_workflow_exception",
    "workflow_error_aggregator",
]
