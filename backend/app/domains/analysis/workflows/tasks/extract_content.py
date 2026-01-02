"""Content extraction task for workflow.

Issue #244: Handle Pattern Integration
- Creates ArtifactRef after extraction for lightweight state passing
- Returns both raw_content (backward compat) and content_ref (new pattern)

Issue #299-304: ArXiv PDF Extraction
- Detects arXiv URLs and routes to ArxivPDFExtractor for full paper content

Issue #602: Trafilatura-First Extraction Strategy
- Standard URLs use Trafilatura (F1=0.958, free, self-hosted) as primary
- Falls back to Jina for SPAs, JS-rendered pages, or low content (<500 words)
- Specialized extractors still used for arXiv, YouTube, GitHub
"""

from app.core.config import settings
from app.core.exception_utils import async_exception_context
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID
from app.db.session import get_session_factory
from app.domains.analysis.services.context.artifact_store import ArtifactStore
from app.domains.analysis.workflows.state import ContentRef
from app.shared.services.extraction.arxiv_pdf_extractor import ArxivPDFExtractor, is_arxiv_url
from app.shared.services.extraction.content_type import detect_content_type
from app.shared.services.extraction.github_extractor import GitHubExtractor, is_github_url
from app.shared.services.extraction.jina_reader import JinaReader
from app.shared.services.extraction.trafilatura_extractor import TrafilaturaExtractor
from app.shared.services.extraction.youtube_extractor import (
    YouTubeExtractor,
    is_youtube_url,
)
from app.shared.services.messaging.sse_helpers import emit_error_event, emit_streaming_event

logger = get_logger(__name__)


async def _extract_with_fallback(
    url: str,
    analysis_id: AnalysisID,
    min_word_count: int = 500,
) -> dict:
    """Extract content using Trafilatura with Jina fallback.

    Tries Trafilatura first (ML-based, high accuracy F1=0.958).
    Falls back to Jina for SPAs/JS-rendered pages or low content.

    Args:
        url: URL to extract content from
        analysis_id: Analysis ID for logging
        min_word_count: Minimum words to accept (default 500)

    Returns:
        ExtractionResult from successful extractor

    """
    # Try Trafilatura first (free, fast, high accuracy)
    trafilatura_extractor = TrafilaturaExtractor()
    try:
        result = await trafilatura_extractor.extract_article(url)
        word_count_value = result.get("word_count", 0)
        word_count = word_count_value if isinstance(word_count_value, int) else 0

        if word_count >= min_word_count:
            logger.info(
                "extraction_trafilatura_success",
                analysis_id=analysis_id,
                url=url,
                word_count=word_count,
                extractor="trafilatura",
            )
            return result

        logger.warning(
            "extraction_trafilatura_low_content",
            analysis_id=analysis_id,
            url=url,
            word_count=word_count,
            min_required=min_word_count,
            action="trying_jina_fallback",
        )
    except Exception as e:  # noqa: BLE001 - Graceful degradation: fallback to Jina on any Trafilatura error
        logger.warning(
            "extraction_trafilatura_failed",
            analysis_id=analysis_id,
            url=url,
            error=str(e),
            action="trying_jina_fallback",
        )
    finally:
        await trafilatura_extractor.close()

    # Fallback to Jina (handles SPAs, JS-rendered pages)
    jina_extractor = JinaReader()
    try:
        result = await jina_extractor.extract_article(url)
        logger.info(
            "extraction_jina_fallback_success",
            analysis_id=analysis_id,
            url=url,
            word_count=result.get("word_count", 0),
            extractor="jina_fallback",
        )
        # Mark as fallback in metadata
        if "metadata" in result and isinstance(result["metadata"], dict):
            result["metadata"]["used_fallback"] = True
            result["metadata"]["primary_extractor"] = "trafilatura"
            result["metadata"]["fallback_extractor"] = "jina"
        return result
    finally:
        await jina_extractor.close()


@robust_traceable(
    name="extract_content",
    run_type="tool",
    tags=["workflow", "node", "extraction"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "analysis",
        "component": "task",
        "task_type": "extraction",
    },
)
async def extract_content(  # noqa: PLR0915, PLR0912
    url: str, analysis_id: AnalysisID, analysis_mode: str = "standard"
) -> dict:
    """Extract content from URL using appropriate extractor.

    Routes to specialized extractors based on URL pattern:
    - arXiv URLs → ArxivPDFExtractor
    - YouTube URLs → YouTubeExtractor
    - GitHub URLs → GitHubExtractor
    - Other URLs → Trafilatura (with Jina fallback)

    Args:
        url: The URL to extract content from
        analysis_id: Unique identifier for this analysis
        analysis_mode: Analysis depth mode (quick, standard, deep_dive)

    Returns:
        Dictionary with 'raw_content' and 'extraction_metadata'

    Raises:
        JinaReaderError: If extraction fails

    """
    # Emit SSE event: extraction started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
        analysis_mode=analysis_mode,
    )

    # Runtime metadata updates
    try:
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id), "url": url},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception as e:  # noqa: BLE001 - Graceful degradation: Langfuse telemetry is optional
        logger.debug(
            "langfuse_telemetry_unavailable", analysis_id=analysis_id, url=url, error=str(e)
        )

    logger.info("workflow_extraction_started", analysis_id=analysis_id, url=url)

    # Route URLs to appropriate extractors based on content type
    # Issue #299-304: ArXiv PDF extraction
    # Issue #602: Trafilatura-first with Jina fallback for standard URLs
    # ROADMAP gap: YouTube and GitHub extractors (now implemented)

    # Handle standard URLs with fallback pattern (no single extractor)
    use_fallback_pattern = False
    extractor: ArxivPDFExtractor | YouTubeExtractor | GitHubExtractor | JinaReader | None = None

    if is_arxiv_url(url):
        logger.info(
            "workflow_extraction_arxiv_detected",
            analysis_id=analysis_id,
            url=url,
        )
        extractor = ArxivPDFExtractor()
    elif is_youtube_url(url):
        logger.info(
            "workflow_extraction_youtube_detected",
            analysis_id=analysis_id,
            url=url,
        )
        extractor = YouTubeExtractor()
    elif is_github_url(url):
        logger.info(
            "workflow_extraction_github_detected",
            analysis_id=analysis_id,
            url=url,
        )
        extractor = GitHubExtractor()
    else:
        # Standard web articles: Use Trafilatura with Jina fallback
        logger.info(
            "workflow_extraction_standard_url",
            analysis_id=analysis_id,
            url=url,
        )
        use_fallback_pattern = True

    try:
        # For standard URLs, use fallback pattern (Trafilatura → Jina)
        if use_fallback_pattern:
            async with async_exception_context(
                operation="extract_content",
                analysis_id=str(analysis_id),
                url=url,
                extractor="TrafilaturaWithJinaFallback",
            ):
                extracted = await _extract_with_fallback(url, analysis_id)
        elif extractor is not None:
            # Specialized extractors (arXiv, YouTube, GitHub)
            async with async_exception_context(
                operation="extract_content",
                analysis_id=str(analysis_id),
                url=url,
                extractor=extractor.__class__.__name__,
            ):
                extracted = await extractor.extract_article(url)
        else:
            # This should never happen - all URL types are covered
            msg = f"No extractor available for URL: {url}"
            raise ValueError(msg)

        # Detect content type from URL
        try:
            detected_content_type = detect_content_type(url)
        except Exception as e:  # noqa: BLE001 - Graceful degradation: content type detection failure should not break extraction
            # Fallback to article if detection fails
            logger.debug(
                "content_type_detection_failed",
                analysis_id=analysis_id,
                url=url,
                error=str(e),
                fallback="article",
            )
            detected_content_type = "article"

        # Get title from extracted metadata
        title = extracted.get("title")
        if not isinstance(title, str):
            title = None

        # Emit SSE event: extraction complete with metadata
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="extraction",
            status="complete",
            word_count=extracted.get("word_count", 0),
            analysis_metadata={
                "title": title,
                "content_type": detected_content_type,
                "url": url,
                "word_count": extracted.get("word_count", 0),
            },
            analysis_mode=analysis_mode,
        )

        logger.info(
            "workflow_extraction_complete",
            analysis_id=analysis_id,
            url=url,
            word_count=extracted.get("word_count", 0),
        )
        # Build extraction_metadata from Jina's metadata plus top-level fields
        # Type-safe construction: start with nested metadata dict, add top-level fields
        base_metadata = extracted.get("metadata")
        metadata: dict[str, str | int | None | bool] = (
            dict(base_metadata) if isinstance(base_metadata, dict) else {}
        )
        title_value = extracted.get("title")
        metadata["title"] = title_value if isinstance(title_value, str) else None
        word_count = extracted.get("word_count")
        metadata["word_count"] = word_count if isinstance(word_count, int) else None

        # Type assertion: extracted["content"] is always str from extractors
        raw_content: str = str(extracted["content"])

        # Add char_count for WorkflowResult validation (Issue #441)
        metadata["char_count"] = len(raw_content)

        # Issue #244: Create ArtifactRef for Handle Pattern
        # This stores content summary and section metadata for on-demand loading
        content_ref = await _create_artifact_ref(
            analysis_id=str(analysis_id),
            content=raw_content,
        )

        logger.info(
            "artifact_ref_created",
            analysis_id=analysis_id,
            uri=content_ref.get("uri"),
            size_bytes=content_ref.get("size_bytes"),
        )

        return {
            "raw_content": raw_content,  # Backward compatibility
            "content_ref": content_ref,  # Issue #244: Handle Pattern
            "extraction_metadata": metadata,
        }
    except Exception as e:
        # Extract error code from exception if available
        from app.core.exceptions import JinaReaderError

        error_code = "EXTRACTION_FAILED"
        if isinstance(e, JinaReaderError):
            # Use the error code from JinaReaderError
            error_code = e.error_code.value

        # Record error to database before emitting events
        from app.domains.analysis.services.persistence.error_recorder import error_recorder

        try:
            await error_recorder.record(
                analysis_id=str(analysis_id),
                error_code=error_code,
                error_message=str(e),
                stage="extraction",
            )
        except Exception as recording_error:  # noqa: BLE001 - Graceful degradation: error recording must not break workflow
            # Don't let error recording break the flow
            logger.debug(
                "error_recorder_unavailable",
                analysis_id=analysis_id,
                error=str(recording_error),
                reason="error_recording_failed_during_extraction_error_handling",
            )

        # Emit error event using standardized helper
        await emit_error_event(
            analysis_id=analysis_id,
            stage="extraction",
            error=str(e),
            error_code=error_code,
            url=url,
        )
        logger.error(
            "workflow_extraction_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        # Close extractor if using specialized extractor (not fallback pattern)
        if extractor is not None:
            await extractor.close()


async def _create_artifact_ref(analysis_id: str, content: str) -> ContentRef:
    """Create artifact reference for Handle Pattern.

    Stores content summary and section metadata in database,
    returns lightweight ref for state passing.

    Args:
        analysis_id: Analysis UUID string
        content: Raw content to create ref for

    Returns:
        ContentRef dict with uri, summary, size_bytes, etc.

    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        store = ArtifactStore(session)
        artifact_ref = await store.create_ref(
            analysis_id=analysis_id,
            content=content,
            content_type="text/markdown",  # Jina returns markdown
        )

        # Convert Pydantic model to ContentRef TypedDict
        return ContentRef(
            uri=artifact_ref.uri,
            summary=artifact_ref.summary,
            size_bytes=artifact_ref.size_bytes,
            content_type=artifact_ref.content_type,
            available_sections=artifact_ref.available_sections,
        )
