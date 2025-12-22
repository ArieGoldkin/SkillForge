"""Workflow orchestration service for analysis workflows."""

import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timeout_config import create_runnable_config
from app.core.tracing import get_current_trace_id, robust_traceable, update_current_trace
from app.db.repositories.artifact_repository import ArtifactRepository
from app.db.session import AsyncSessionLocal
from app.domains.analysis.schemas.api import AnalysisStatus
from app.domains.analysis.services.events import WorkflowEventEmitter
from app.domains.analysis.services.persistence import DataPersister, StatusUpdater
from app.domains.analysis.services.workflow import handle_workflow_exception
from app.domains.analysis.services.workflow.validator import validate_workflow_result
from app.domains.analysis.workflows.analysis import analysis_workflow

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates analysis workflow execution and post-processing."""

    def __init__(self) -> None:
        """Initialize orchestrator with service dependencies."""
        self.status_updater = StatusUpdater()
        self.data_persister = DataPersister()
        self.event_emitter = WorkflowEventEmitter()

    @robust_traceable(
        name="analysis_workflow",
        run_type="chain",
        tags=["workflow", "analysis"],
        metadata={
            "environment": settings.ENVIRONMENT,
            "workflow_type": "analysis",
        },
    )
    async def run(
        self, analysis_id: uuid.UUID, url: str, skill_level: str = "intermediate"
    ) -> None:
        """Run analysis workflow and handle post-processing.

        Executes the workflow, validates results, persists data, validates artifacts,
        and updates status. Emits SSE events for progress tracking.

        The robust_traceable decorator ensures LangGraph's internal node/LLM traces
        nest properly under this outer trace in Langfuse.

        Exception handling is done at the application boundary (this method) where
        we have context (analysis_id, status updates). GeneratorExit exceptions are
        handled by the unified handle_workflow_exception() helper.

        Args:
            analysis_id: UUID of the analysis
            url: URL to analyze
            skill_level: User's experience level (beginner, intermediate, expert)

        """
        workflow_completed = False  # Track completion status for GeneratorExit handling

        # Runtime metadata updates for Langfuse
        update_current_trace(
            metadata={
                "analysis_id": str(analysis_id),
                "url": url,
                "workflow_version": "1.0",
            },
            tags=["analysis", "workflow"],
            session_id=f"analysis-{analysis_id}",  # Group all traces for this analysis
            user_id="anonymous",  # Will be dynamic after auth implementation
        )

        try:
            logger.info(
                "workflow_task_started",
                analysis_id=str(analysis_id),
                url=url,
            )

            # Create config with thread_id for checkpointing
            # Note: Workflow-level timeout is handled by step_timeout on graph
            config = create_runnable_config(
                thread_id=str(analysis_id),
                metadata={
                    "analysis_id": str(analysis_id),
                    "url": url,
                    "task_type": "analysis_workflow",
                    "skill_level": skill_level,
                },
                tags=["workflow", "analysis", f"analysis:{analysis_id}"],
            )

            # Issue #384: Verify Langfuse callback handler is present for graph visualization
            # The callback handler enables automatic graph structure inference in Langfuse UI
            callbacks_enabled = bool(config.get("callbacks"))
            if callbacks_enabled:
                logger.debug(
                    "langfuse_callback_enabled",
                    analysis_id=str(analysis_id),
                    message="Langfuse CallbackHandler present - graph visualization enabled",
                )
            else:
                logger.debug(
                    "langfuse_callback_disabled",
                    analysis_id=str(analysis_id),
                    message="Langfuse disabled or not configured - graph visualization unavailable",
                )

            input_state: dict[str, str] = {
                "url": url,
                "analysis_id": str(analysis_id),
                "skill_level": skill_level,
            }

            # Execute workflow with callbacks (Issue #384: enables graph visualization)
            logger.debug(
                "workflow_execution_starting",
                analysis_id=str(analysis_id),
                url=url,
                thread_id=str(analysis_id),
                callbacks_enabled=callbacks_enabled,
            )
            result = await analysis_workflow.ainvoke(input_state, config=config)  # type: ignore[arg-type]
            logger.debug(
                "workflow_execution_completed",
                analysis_id=str(analysis_id),
                result_keys=list(result.keys()) if isinstance(result, dict) else "non-dict",
            )

            logger.info(
                "workflow_task_complete",
                analysis_id=str(analysis_id),
            )

            # Persist workflow data to analysis record (Issue #168)
            # This enables full-text search (search_vector trigger) and semantic search
            if isinstance(result, dict):
                missing_fields = validate_workflow_result(result)
                if missing_fields:
                    logger.error(
                        "workflow_result_incomplete",
                        analysis_id=str(analysis_id),
                        missing_fields=missing_fields,
                        message="Workflow result missing required fields",
                    )
                    await self.status_updater.update(
                        analysis_id, AnalysisStatus.ANALYSIS_FAILED.value
                    )
                    await self.event_emitter.emit_error(
                        analysis_id,
                        ValueError(f"Workflow result incomplete: missing {missing_fields}"),
                    )
                    return

                persist_success = await self.data_persister.persist(analysis_id, result)
                if not persist_success:
                    logger.error(
                        "workflow_persistence_failed",
                        analysis_id=str(analysis_id),
                        message="Failed to persist workflow data, marking as failed",
                    )
                    await self.status_updater.update(
                        analysis_id, AnalysisStatus.ANALYSIS_FAILED.value
                    )
                    await self.event_emitter.emit_error(
                        analysis_id,
                        RuntimeError("Workflow data persistence failed"),
                    )
                    return

            # Validate artifact exists before marking analysis complete
            # This ensures data integrity - analyses should not be marked complete without artifacts
            async with AsyncSessionLocal() as db_session:
                repository = ArtifactRepository(session=db_session)
                artifact = await repository.get_artifact_by_analysis_id(analysis_id)

                if not artifact:
                    logger.error(
                        "workflow_complete_without_artifact",
                        analysis_id=str(analysis_id),
                        error="Artifact generation failed or was skipped",
                    )
                    # Use semantic status: artifact_failed (workflow done, but no artifact)
                    await self.status_updater.update(
                        analysis_id, AnalysisStatus.ARTIFACT_FAILED.value
                    )
                    await self.event_emitter.emit_error(
                        analysis_id,
                        ValueError("Workflow completed but no artifact was generated"),
                    )
                    return

            # Update Analysis status to complete (only if artifact exists and is valid)
            await self.status_updater.update(analysis_id, AnalysisStatus.COMPLETE.value)

            # Emit completion event with artifact_id per SSE_SCHEMA.md
            # Also attach artifact info to Langfuse trace for visibility
            try:
                # Get trace_id for frontend feedback submission (Issue #385)
                trace_id = get_current_trace_id()

                # Re-query artifact for SSE event (artifact variable from validation is out of scope)
                async with AsyncSessionLocal() as db_session:
                    repository = ArtifactRepository(session=db_session)
                    artifact = await repository.get_artifact_by_analysis_id(analysis_id)

                    artifact_id = str(artifact.id) if artifact else None
                    await self.event_emitter.emit_completion(analysis_id, artifact_id, trace_id)
            except Exception as event_error:
                logger.error(
                    "workflow_complete_event_failed",
                    analysis_id=str(analysis_id),
                    error=str(event_error),
                    exc_info=True,
                )
                # Don't raise - workflow completed successfully, event emission is secondary
            workflow_completed = True

        except (GeneratorExit, RuntimeError, BaseException) as exc:  # noqa: BLE001
            # Unified exception handling for all workflow exceptions
            # Python's async runtime converts GeneratorExit to RuntimeError in async functions
            # The handler normalizes both cases and handles them consistently
            # BaseException needed to catch GeneratorExit which doesn't inherit from Exception
            await handle_workflow_exception(exc, analysis_id, workflow_completed)
