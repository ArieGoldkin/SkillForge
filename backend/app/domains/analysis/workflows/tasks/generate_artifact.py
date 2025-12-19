"""Generate markdown artifact from aggregated insights.

This module implements the artifact generation node that creates a
comprehensive markdown document from aggregated agent findings.
"""

import time
import uuid

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.logging import get_logger
from app.core.template_utils import render_jinja_template
from app.core.tracing import robust_traceable
from app.db.repositories.artifact_repository import ArtifactRepository
from app.db.session import get_session_factory
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import (
    get_agent_findings,
    get_aggregated_insights,
    get_extraction_metadata,
)
from app.domains.analysis.workflows.tasks.aggregation.validation import validate_and_parse_findings
from app.domains.analysis.workflows.tasks.artifact_helpers import (
    build_claude_code_prompt,
    extract_artifact_metadata,
)
from app.shared.services.messaging.sse_helpers import emit_streaming_event
from app.shared.services.utils.markdown import sanitize_markdown

logger = get_logger(__name__)


async def _submit_artifact_quality_scores(
    artifact_content: str,
    aggregated_insights: dict,
    analysis_id: str,
) -> None:
    """Submit G-Eval quality scores for the generated artifact to Langfuse.

    This function runs after artifact storage to provide detailed quality
    assessment without blocking the user. Scores appear in Langfuse UI for
    quality analytics and trend analysis.

    Args:
        artifact_content: The generated markdown artifact content
        aggregated_insights: The aggregated insights used to generate the artifact
        analysis_id: The analysis ID for logging context

    """
    try:
        from app.core.tracing import get_current_trace_id
        from app.shared.services.g_eval import g_eval_score

        # Get current trace ID to link scores to this artifact generation
        trace_id = get_current_trace_id()

        if not trace_id:
            logger.debug(
                "artifact_g_eval_skipped_no_trace",
                analysis_id=analysis_id,
                message="No trace context available for G-Eval scoring",
            )
            return

        # Prepare input content for G-Eval (what was used to create the artifact)
        # Use the aggregated insights summary as the "input" that generated this "output"
        input_summary = aggregated_insights.get("summary", "")
        if not input_summary:
            # Fallback to a generic description if summary is missing
            input_summary = "Generate a comprehensive technical implementation guide from the aggregated agent findings."

        logger.info(
            "artifact_g_eval_scoring_started",
            analysis_id=analysis_id,
            trace_id=trace_id,
            artifact_length=len(artifact_content),
        )

        # Score the artifact using G-Eval with artifact-specific criteria
        # Use agent_type="artifact_generator" for artifact-specific rubrics
        g_eval_result = await g_eval_score(
            input_content=input_summary,
            output=artifact_content,
            agent_type="artifact_generator",
            trace_id=trace_id,
            use_cache=True,
        )

        logger.info(
            "artifact_g_eval_scoring_complete",
            analysis_id=analysis_id,
            trace_id=trace_id,
            overall_score=g_eval_result.overall,
            completeness=g_eval_result.completeness,
            accuracy=g_eval_result.accuracy,
            coherence=g_eval_result.coherence,
            depth=g_eval_result.depth,
            confidence=g_eval_result.confidence,
        )

    except Exception as e:  # noqa: BLE001 - Graceful degradation for quality scoring
        # Don't fail artifact generation if G-Eval scoring fails
        logger.warning(
            "artifact_g_eval_scoring_failed",
            analysis_id=analysis_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )


@robust_traceable(
    name="generate_artifact",
    run_type="chain",
    tags=["workflow", "node", "artifact_generation"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "analysis",
        "component": "task",
        "task_type": "artifact_generation",
    },
)
async def generate_artifact(
    state: AnalysisState,
) -> dict[str, object]:
    """Generate markdown artifact from aggregated insights.

    Creates a comprehensive markdown document from aggregated agent findings,
    stores it in the database, and returns the artifact ID.

    Args:
        state: Current workflow state with aggregated_insights populated

    Returns:
        Dictionary with artifact_id field (to avoid LangGraph concurrent update errors)

    Raises:
        ValueError: If aggregated_insights is missing or invalid
        Exception: If database operation fails

    """
    analysis_id = state["analysis_id"]
    aggregated_insights = get_aggregated_insights(state)
    agent_findings = get_agent_findings(state)
    extraction_metadata = get_extraction_metadata(state)
    url = state.get("url", "")

    # Extract agent_statuses from aggregated_insights
    agent_statuses = (
        aggregated_insights.get("agent_statuses", {})
        if isinstance(aggregated_insights, dict)
        else {}
    )

    start_time = time.time()

    # Emit SSE event: artifact generation started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=get_stage_name("artifact_generation"),
        status="running",
    )

    # Runtime metadata updates
    try:
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id)},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception:  # noqa: BLE001 - Langfuse may not be available
        pass

    logger.info(
        "workflow_artifact_generation_started",
        analysis_id=analysis_id,
    )

    try:
        # Validate aggregated_insights exists
        if not aggregated_insights or not isinstance(aggregated_insights, dict):
            error_msg = "aggregated_insights is missing or invalid"
            logger.error(
                "workflow_artifact_generation_missing_insights",
                analysis_id=analysis_id,
            )
            raise ValueError(error_msg)

        # Prepare template context
        title = extraction_metadata.get("title") or "Technical Analysis"
        generated_date = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        analysis_metadata = {
            "title": title,
            "url": url,
            "generated_date": generated_date,
            "analysis_id": str(analysis_id),
        }

        # Build Claude Code prompt
        claude_code_prompt = build_claude_code_prompt(aggregated_insights, analysis_metadata)

        # Filter out empty/invalid findings before template rendering
        validated_findings, _, _ = validate_and_parse_findings(agent_findings)

        # Render markdown template
        # Extract quick_reference from aggregated_insights for template access
        quick_reference = (
            aggregated_insights.get("quick_reference") if aggregated_insights else None
        )

        template_context = {
            "aggregated_insights": aggregated_insights,
            "agent_findings": validated_findings,
            "analysis_metadata": analysis_metadata,
            "claude_code_prompt": claude_code_prompt,
            "quick_reference": quick_reference,  # Pass at top level for template
            "agent_statuses": agent_statuses,  # Pass agent statuses for template display
        }

        markdown_content = render_jinja_template("artifact.j2", template_context)

        # Sanitize markdown to fix LLM-generated formatting issues
        # This fixes tables with blank lines and unicode bullets
        markdown_content = sanitize_markdown(markdown_content)

        # Extract metadata (topics, complexity)
        artifact_metadata = extract_artifact_metadata(aggregated_insights, agent_findings)

        # Store artifact in database using repository pattern
        session_factory = get_session_factory()
        async with session_factory() as db_session:
            repository = ArtifactRepository(session=db_session)
            artifact = await repository.create_artifact(
                {
                    "id": uuid.uuid4(),
                    "analysis_id": analysis_id,
                    "markdown_content": markdown_content,
                    "version": 1,
                    "artifact_metadata": artifact_metadata,
                    "download_count": 0,
                }
            )
            artifact_id = str(artifact.id)

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "workflow_artifact_generation_complete",
            analysis_id=analysis_id,
            artifact_id=artifact_id,
            markdown_length=len(markdown_content),
            processing_time_ms=processing_time_ms,
        )

        # Emit SSE event: artifact generation complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("artifact_generation"),
            status="complete",
            artifact_id=artifact_id,
            markdown_length=len(markdown_content),
        )

        # Issue #378-385: Submit G-Eval scores to Langfuse for artifact quality
        # This happens after artifact is stored, so it doesn't block user display
        await _submit_artifact_quality_scores(
            artifact_content=markdown_content,
            aggregated_insights=aggregated_insights,
            analysis_id=analysis_id,
        )

        # Return only updated fields, not entire state
        return {"artifact_id": artifact_id}

    except Exception as e:
        # Emit SSE event: artifact generation failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage=get_stage_name("artifact_generation"),
            status="failed",
            error=str(e),
            error_code="ARTIFACT_GENERATION_FAILED",
        )

        logger.error(
            "workflow_artifact_generation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
