"""Workflow orchestration service for analysis workflows."""

from typing import Any

from app.core.branded_ids import AnalysisID
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
from app.domains.analysis.services.workflow.validator import WorkflowResultValidator

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates analysis workflow execution and post-processing."""

    def __init__(self, workflow: Any) -> None:
        """Initialize orchestrator with workflow instance.

        Args:
            workflow: Compiled workflow graph instance (required)

        """
        self.workflow = workflow
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
    async def run(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        analysis_id: AnalysisID,
        url: str,
        skill_level: str = "intermediate",
        analysis_mode: str = "standard",
        start_from_stage: str | None = None,
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
            analysis_mode: Analysis depth mode (quick, standard, deep_dive) - Issue #436
            start_from_stage: Optional stage to start from for retry/rerun workflows (Issue #544)
                            - None or "pending" or "extracting": Normal flow from extraction
                            - "analyzing": Skip extraction/embedding (reuse from DB), restart from supervisor
                            - "generating_artifact": Not yet implemented, falls back to "analyzing"

                            When a stage is specified, the orchestrator:
                            1. Loads existing data from DB (raw_content, embeddings, etc.)
                            2. Sets skip flags in state (skip_extraction, skip_embedding)
                            3. Graph nodes check skip flags and bypass work if already done

        """
        workflow_completed = False  # Track completion status for GeneratorExit handling

        # Runtime metadata updates for Langfuse
        update_current_trace(
            metadata={
                "analysis_id": str(analysis_id),
                "url": url,
                "workflow_version": "1.0",
                "analysis_mode": analysis_mode,
            },
            tags=["analysis", "workflow", f"mode:{analysis_mode}"],
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
                    "analysis_mode": analysis_mode,
                },
                tags=["workflow", "analysis", f"analysis:{analysis_id}", f"mode:{analysis_mode}"],
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

            # Build initial state - may be augmented with existing data for retry/rerun
            input_state: dict[str, Any] = {
                "url": url,
                "analysis_id": str(analysis_id),
                "skill_level": skill_level,
                "analysis_mode": analysis_mode,  # Issue #436: Tier-based agent filtering
            }

            # Issue #544: Load existing data when starting from intermediate stage
            if start_from_stage and start_from_stage not in ["pending", "extracting"]:
                from app.db.repositories.analysis_repository import AnalysisRepository

                async with AsyncSessionLocal() as db_session:
                    repo = AnalysisRepository(session=db_session)
                    existing_analysis = await repo.get_by_id(analysis_id, validate=False)

                    if not existing_analysis:
                        logger.error(
                            "retry_analysis_not_found",
                            analysis_id=str(analysis_id),
                            start_from_stage=start_from_stage,
                        )
                        await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                        await self.event_emitter.emit_error(
                            analysis_id,
                            ValueError(
                                f"Analysis {analysis_id} not found for retry from {start_from_stage}"
                            ),
                            stage="validation",
                        )
                        return

                    # Load existing data based on start stage
                    if start_from_stage == "analyzing":
                        # Reuse extraction and embedding, restart from supervisor
                        if not existing_analysis.raw_content:
                            logger.error(
                                "retry_missing_raw_content",
                                analysis_id=str(analysis_id),
                            )
                            await self.status_updater.update(
                                analysis_id, AnalysisStatus.FAILED.value
                            )
                            await self.event_emitter.emit_error(
                                analysis_id,
                                ValueError(
                                    "Cannot restart from analyzing stage: missing raw_content"
                                ),
                                stage="validation",
                            )
                            return

                        # Load extraction data into state
                        input_state["raw_content"] = existing_analysis.raw_content
                        input_state["content_type"] = existing_analysis.content_type
                        if existing_analysis.extraction_metadata:
                            input_state["extraction_metadata"] = (
                                existing_analysis.extraction_metadata
                            )
                        if existing_analysis.content_embedding:
                            input_state["content_embedding"] = existing_analysis.content_embedding

                        # Set skip flags so graph bypasses extraction/embedding nodes
                        # These flags are checked by conditional edges in graph_builder
                        input_state["skip_extraction"] = True
                        input_state["skip_embedding"] = True
                        input_state["extraction_status"] = "success"  # Mark as already completed

                        logger.info(
                            "retry_loaded_extraction_data",
                            analysis_id=str(analysis_id),
                            start_from_stage=start_from_stage,
                            skip_extraction=True,
                            skip_embedding=True,
                        )

                    elif start_from_stage == "generating_artifact":
                        # Reuse everything up to aggregation, restart from artifact generation
                        # Note: This requires aggregated_insights to be stored in DB
                        # For now, log warning and fall back to "analyzing" stage
                        logger.warning(
                            "retry_artifact_stage_not_implemented",
                            analysis_id=str(analysis_id),
                            message="generating_artifact stage requires persisted aggregated_insights - falling back to analyzing",
                        )
                        # Fall back to analyzing stage
                        if existing_analysis.raw_content:
                            input_state["raw_content"] = existing_analysis.raw_content
                            input_state["content_type"] = existing_analysis.content_type
                            if existing_analysis.extraction_metadata:
                                input_state["extraction_metadata"] = (
                                    existing_analysis.extraction_metadata
                                )
                            if existing_analysis.content_embedding:
                                input_state["content_embedding"] = (
                                    existing_analysis.content_embedding
                                )

                            # Set skip flags for fallback to analyzing stage
                            input_state["skip_extraction"] = True
                            input_state["skip_embedding"] = True
                            input_state["extraction_status"] = "success"

            # Execute workflow with callbacks (Issue #384: enables graph visualization)
            logger.debug(
                "workflow_execution_starting",
                analysis_id=str(analysis_id),
                url=url,
                thread_id=str(analysis_id),
                callbacks_enabled=callbacks_enabled,
            )
            result = await self.workflow.ainvoke(input_state, config=config)
            logger.debug(
                "workflow_execution_completed",
                analysis_id=str(analysis_id),
                result_keys=list(result.keys()) if isinstance(result, dict) else "non-dict",
            )

            logger.info(
                "workflow_task_complete",
                analysis_id=str(analysis_id),
            )

            # Check workflow status before validation
            workflow_status = result.get("workflow_status") if isinstance(result, dict) else None

            if workflow_status == "failed":
                # Failed workflow - skip validation (expected incomplete)
                logger.debug(
                    "workflow_failed",
                    analysis_id=str(analysis_id),
                    message="Workflow failed, skipping validation",
                )
                # Status and error already set by workflow_failed node
                return

            if workflow_status == "completed":
                # Completed workflow - validate all fields
                if not isinstance(result, dict):
                    logger.error(
                        "workflow_result_not_dict",
                        analysis_id=str(analysis_id),
                        result_type=type(result).__name__,
                    )
                    # Use generic "failed" status to avoid transition issues
                    # (analysis might be in various states when this error occurs)
                    await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                    await self.event_emitter.emit_error(
                        analysis_id,
                        TypeError(f"Workflow result must be dict, got {type(result)}"),
                        stage="validation",  # Orchestrator-level validation error
                    )
                    return

                validator = WorkflowResultValidator()
                validated_result, errors = validator.validate(result, "completed")

                if errors:
                    # Validation failed - this is unexpected for completed workflows
                    logger.error(
                        "workflow_result_validation_failed",
                        analysis_id=str(analysis_id),
                        errors=errors,
                        message="Completed workflow has invalid data",
                    )
                    # Use generic "failed" status to avoid transition issues
                    # (analysis might be in various states when validation fails)
                    await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                    await self.event_emitter.emit_error(
                        analysis_id,
                        ValueError(f"Data validation failed: {errors}"),
                        stage="validation",  # Orchestrator-level validation error
                    )
                    return

                # Validation passed - persist validated data
                if validated_result is None:
                    # Should not happen, but handle gracefully
                    logger.error(
                        "workflow_result_validation_returned_none",
                        analysis_id=str(analysis_id),
                        message="Validator returned None despite no errors",
                    )
                    # Use generic "failed" status to avoid transition issues
                    await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                    await self.event_emitter.emit_error(
                        analysis_id,
                        ValueError("Validation returned None unexpectedly"),
                        stage="validation",  # Orchestrator-level validation error
                    )
                    return

                try:
                    await self.data_persister.persist(analysis_id, validated_result.model_dump())
                except ValueError as validation_error:
                    # Persister validation failed (shouldn't happen, but handle gracefully)
                    logger.exception(
                        "persister_validation_failed",
                        analysis_id=str(analysis_id),
                        error=str(validation_error),
                    )
                    # Use generic "failed" status to avoid transition issues
                    await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                    await self.event_emitter.emit_error(
                        analysis_id,
                        validation_error,
                        stage="persistence",  # Orchestrator-level persistence validation error
                    )
                    return
                except RuntimeError as db_error:
                    # Database error
                    logger.exception(
                        "workflow_persistence_failed",
                        analysis_id=str(analysis_id),
                        error=str(db_error),
                    )
                    # Use generic "failed" status to avoid transition issues
                    await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                    await self.event_emitter.emit_error(
                        analysis_id,
                        db_error,
                        stage="persistence",  # Orchestrator-level database error
                    )
                    return

            else:
                # Invalid or missing workflow status
                # This typically means the workflow encountered an unexpected error
                # Check if a node-level error was already emitted before emitting orchestrator error
                logger.error(
                    "invalid_workflow_status",
                    analysis_id=str(analysis_id),
                    status=workflow_status,
                    message="Workflow returned invalid or missing status",
                )
                # Use generic "failed" status to avoid transition issues
                await self.status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
                # emit_error() will check for recent errors and skip if node already emitted
                await self.event_emitter.emit_error(
                    analysis_id,
                    ValueError(f"Invalid workflow status: {workflow_status}"),
                    stage="validation",  # Orchestrator-level validation error
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
                        stage="validation",  # Orchestrator-level validation error (artifact check)
                    )
                    return

            # Update Analysis status to complete (only if artifact exists and is valid)
            await self.status_updater.update(analysis_id, AnalysisStatus.COMPLETE.value)

            # Emit completion event with artifact_id per SSE_SCHEMA.md
            # Also attach artifact info to Langfuse trace for visibility
            try:
                # Get trace_id for frontend feedback submission (Issue #385)
                trace_id = get_current_trace_id()

                # Re-query artifact for SSE event
                # (artifact variable from validation is out of scope)
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
