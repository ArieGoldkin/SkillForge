"""Error aggregation service for workflow-level error detection.

Issue #627 & #628: Aggregates agent-level errors to detect workflow-level failures
and ensures proper SSE error events and DB persistence.

When individual agents fail (timeout, error), they return empty findings and
the workflow continues. This service detects when enough failures occurred
to constitute a workflow-level failure, then:
1. Emits SSE error event to frontend (#627)
2. Records error details to Analysis table (#628)
"""

from typing import Any

from app.core.branded_ids import AnalysisID
from app.core.logging import get_logger
from app.domains.analysis.services.events import WorkflowEventEmitter
from app.domains.analysis.services.persistence.error_recorder import error_recorder
from app.domains.analysis.workflows.tier_types import TIER_1_AGENTS

logger = get_logger(__name__)

# Threshold for critical failure: if >= this % of Tier 1 agents fail, workflow fails
TIER1_FAILURE_THRESHOLD = 0.5  # 50%

# Minimum expected findings for a successful workflow
MIN_EXPECTED_FINDINGS = 2


class WorkflowErrorAggregator:
    """Aggregates agent-level failures to detect workflow-level errors.

    This service is called after workflow completion to check if the
    workflow should be considered failed despite completing execution.

    Scenarios detected:
    - Too many Tier 1 agents failed (>= 50%)
    - No agent findings produced (empty synthesis input)
    - Critical timeouts at synthesis/aggregation stage
    """

    def __init__(self) -> None:
        """Initialize the error aggregator."""
        self.event_emitter = WorkflowEventEmitter()

    async def check_and_record_errors(
        self,
        analysis_id: AnalysisID,
        workflow_result: dict[str, Any],
    ) -> bool:
        """Check workflow result for aggregated failures and record if found.

        Args:
            analysis_id: UUID of the analysis
            workflow_result: Final workflow state dict

        Returns:
            True if workflow has critical failures (should be marked failed),
            False if workflow completed successfully.

        """
        # Detect any failure condition and record if found
        error_info = self._detect_failure(workflow_result)

        if error_info:
            error_code, error_message, stage = error_info
            await self._record_workflow_failure(analysis_id, error_code, error_message, stage)
            return True

        # Log success
        findings = workflow_result.get("agent_findings", [])
        logger.debug(
            "error_aggregator_no_failures",
            analysis_id=str(analysis_id),
            findings_count=len(findings),
            message="No aggregated failures detected",
        )
        return False

    def _detect_failure(  # noqa: PLR0911 - Multiple return statements for clear error categorization
        self, workflow_result: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """Detect workflow failure conditions.

        Returns (error_code, error_message, stage) if failure detected, None otherwise.
        """
        # Check 1: Workflow already marked as failed
        if workflow_result.get("workflow_status") == "failed":
            return (
                "WORKFLOW_FAILED",
                workflow_result.get("final_error") or "Workflow marked as failed",
                workflow_result.get("failed_at_stage") or "unknown",
            )

        # Check 2: Should abort flag was set
        if workflow_result.get("should_abort"):
            return (
                "WORKFLOW_ABORTED",
                workflow_result.get("abort_reason") or "Workflow aborted",
                workflow_result.get("extraction_status") or "unknown",
            )

        # Check 3: Quality gate failed and not retried successfully
        if workflow_result.get("quality_gate_error"):
            return (
                "QUALITY_GATE_FAILED",
                workflow_result.get("quality_gate_error"),
                "quality_gate",
            )

        # Checks 4 & 5 only apply if workflow is NOT marked as "completed"
        # If workflow_status == "completed", the workflow engine already determined success
        if workflow_result.get("workflow_status") == "completed":
            return None

        # Check 4: Too many Tier 1 agents failed (only for non-completed workflows)
        tier1_failure = self._check_tier1_failures(workflow_result)
        if tier1_failure:
            return ("TIER1_CRITICAL_FAILURE", tier1_failure, "agents")

        # Check 5: No findings produced (only for non-completed workflows)
        findings = workflow_result.get("agent_findings", [])
        if len(findings) < MIN_EXPECTED_FINDINGS:
            return (
                "INSUFFICIENT_FINDINGS",
                f"Only {len(findings)} findings produced (minimum: {MIN_EXPECTED_FINDINGS})",
                "aggregation",
            )

        return None

    def _check_tier1_failures(self, workflow_result: dict[str, Any]) -> str | None:
        """Check if too many Tier 1 agents failed.

        Returns error message if threshold exceeded, None otherwise.
        """
        findings = workflow_result.get("agent_findings", [])
        dispatched = workflow_result.get("dispatched_agents", [])

        if not dispatched:
            # Can't determine failure rate without dispatch info
            return None

        # Count Tier 1 agents that were dispatched
        tier1_dispatched = [a for a in dispatched if a in TIER_1_AGENTS]
        if not tier1_dispatched:
            return None

        # Count Tier 1 agents that produced findings
        tier1_with_findings = set()
        for finding in findings:
            agent_type = finding.get("agent_type")
            if agent_type in TIER_1_AGENTS:
                tier1_with_findings.add(agent_type)

        # Calculate failure rate
        tier1_failed = len(tier1_dispatched) - len(tier1_with_findings)
        failure_rate = tier1_failed / len(tier1_dispatched)

        if failure_rate >= TIER1_FAILURE_THRESHOLD:
            failed_agents = [a for a in tier1_dispatched if a not in tier1_with_findings]
            return (
                f"Critical Tier 1 agent failures: {tier1_failed}/{len(tier1_dispatched)} "
                f"({failure_rate:.0%}) failed. Failed agents: {', '.join(failed_agents)}"
            )

        return None

    async def _record_workflow_failure(
        self,
        analysis_id: AnalysisID,
        error_code: str,
        error_message: str,
        stage: str,
    ) -> None:
        """Record workflow failure to DB and emit SSE error event.

        Issue #627: Emit SSE error event
        Issue #628: Record error details to Analysis table
        """
        logger.warning(
            "error_aggregator_failure_detected",
            analysis_id=str(analysis_id),
            error_code=error_code,
            error_message=error_message[:200],  # Truncate for log
            stage=stage,
        )

        # Issue #628: Record to database
        try:
            await error_recorder.record(
                analysis_id=str(analysis_id),
                error_code=error_code,
                error_message=error_message,
                stage=stage,
            )
        except Exception as db_error:  # noqa: BLE001 - Graceful degradation
            # Issue #628 fix: Log at WARNING (not DEBUG) so failures are visible
            logger.warning(
                "error_aggregator_db_record_failed",
                analysis_id=str(analysis_id),
                error_code=error_code,
                db_error=str(db_error),
                message="Failed to record error to database - continuing with SSE event",
            )

        # Issue #627: Emit SSE error event
        try:
            from app.shared.services.messaging.sse_helpers import emit_error_event

            await emit_error_event(
                analysis_id=str(analysis_id),
                stage=stage,
                error=error_message,
                error_code=error_code,
            )
            logger.info(
                "error_aggregator_sse_emitted",
                analysis_id=str(analysis_id),
                error_code=error_code,
            )
        except Exception as sse_error:  # noqa: BLE001 - Graceful degradation
            logger.warning(
                "error_aggregator_sse_failed",
                analysis_id=str(analysis_id),
                error_code=error_code,
                sse_error=str(sse_error),
                message="Failed to emit SSE error event",
            )


# Singleton instance
workflow_error_aggregator = WorkflowErrorAggregator()
