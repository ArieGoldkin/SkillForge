"""MCP Tools for Handle Pattern artifact loading.

Provides LangChain tools that agents can use to load content from artifact refs.
Implements the "reactive" pattern: agents request content only when needed.

Reference: Google ADK Context Engineering - Handle Pattern
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.schemas.context import ArtifactSection
from app.services.context.artifact_store import (
    ArtifactNotFoundError,
    ArtifactStore,
    InvalidURIError,
)

logger = get_logger(__name__)


class LoadArtifactInput(BaseModel):
    """Input schema for load_artifact tool.

    Using Pydantic model for clear parameter documentation.
    """

    uri: str = Field(description="Artifact URI in format 'analysis://{analysis_id}/content'")
    section: str = Field(
        default="summary",
        description=(
            "Content section to load: 'summary' (default), 'full', 'first_n', "
            "'code_blocks', or 'headings'"
        ),
    )
    max_chars: int | None = Field(
        default=None,
        description="Maximum characters to return (for 'full' or 'first_n' sections)",
    )


@tool(args_schema=LoadArtifactInput)
async def load_artifact(uri: str, section: str = "summary", max_chars: int | None = None) -> str:
    """Load content from an artifact reference.

    Use this tool to retrieve content from artifact URIs (analysis://{id}/content).
    Instead of having full content in state, agents receive lightweight refs
    and call this tool to load specific sections on-demand.

    Available sections:
    - summary: Always-available summary (~500 words) - FASTEST
    - full: Complete content (may be large) - use max_chars to limit
    - first_n: First N characters (default 5000) - good for previews
    - code_blocks: Just the code blocks - useful for implementation agents
    - headings: Document outline - useful for structure overview

    Examples:
        # Load summary (default, recommended first)
        load_artifact(uri="analysis://abc-123/content")

        # Load code blocks for implementation review
        load_artifact(uri="analysis://abc-123/content", section="code_blocks")

        # Load first 10000 chars for deeper analysis
        load_artifact(uri="analysis://abc-123/content", section="first_n", max_chars=10000)

    """
    # Map string section to enum
    try:
        section_enum = ArtifactSection(section.lower())
    except ValueError:
        return f"Invalid section '{section}'. Valid options: summary, full, first_n, code_blocks, headings"

    logger.info(
        "load_artifact_called",
        uri=uri,
        section=section,
        max_chars=max_chars,
    )

    # Create session and load content
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            store = ArtifactStore(session)
            content = await store.load(
                uri=uri,
                section=section_enum,
                max_chars=max_chars,
            )
            logger.info(
                "load_artifact_success",
                uri=uri,
                section=section,
                content_length=len(content),
            )
            return content

        except InvalidURIError as e:
            logger.warning("load_artifact_invalid_uri", uri=uri, error=str(e))
            return f"Error: Invalid artifact URI format. Expected 'analysis://{{id}}/content'. Got: {uri}"

        except ArtifactNotFoundError as e:
            logger.warning("load_artifact_not_found", uri=uri, error=str(e))
            return f"Error: Artifact not found for URI: {uri}"

        except Exception as e:
            logger.exception("load_artifact_error", uri=uri, error=str(e))
            return f"Error loading artifact: {e!s}"


# Tool configuration for registry
ARTIFACT_TOOL_CONFIG = {
    "name": "load_artifact",
    "description": "Load content sections from artifact URIs (Handle Pattern)",
    "server": "skillforge",  # Internal tool server
}


# List of all artifact tools
ARTIFACT_TOOLS = [load_artifact]
