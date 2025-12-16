"""MCP Tools for Agent Memory (RAG).

Provides LangChain tools for agents to search past analyses and patterns.
Implements "reactive recall" - agents request memories when they recognize gaps.

Issue #245: Agent Memory Access (RAG)
Reference: Google ADK Context Engineering - Reactive Recall Pattern
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.agent_memory import MemoryType
from app.shared.services.memory import AgentMemoryService

logger = get_logger(__name__)


class SearchMemoryInput(BaseModel):
    """Input schema for search_memory tool."""

    query: str = Field(description="Search query describing what knowledge you need")
    memory_type: str = Field(
        default="all",
        description=(
            "Filter by memory type: 'all' (default), 'analysis_summary', "
            "'vulnerability_pattern', 'best_practice', 'agent_finding'"
        ),
    )
    limit: int = Field(
        default=5,
        description="Maximum number of results to return (1-10)",
        ge=1,
        le=10,
    )


@tool(args_schema=SearchMemoryInput)
async def search_memory(
    query: str,
    memory_type: str = "all",
    limit: int = 5,
) -> str:
    """Search past analyses and findings for relevant context.

    Use this tool when you need to:
    - Find similar past analyses for comparison
    - Look up known vulnerability patterns
    - Reference previously identified best practices
    - Check what other agents found in similar content

    The tool searches through stored memories using semantic similarity,
    returning the most relevant results that exceed a quality threshold.

    Memory Types:
    - analysis_summary: Condensed summaries of past analyses
    - vulnerability_pattern: Known security vulnerability patterns
    - best_practice: Learned best practices and recommendations
    - agent_finding: Individual findings from past agent executions
    - all: Search across all memory types (default)

    Examples:
        # Find similar security vulnerabilities
        search_memory(query="XSS vulnerabilities in React apps", memory_type="vulnerability_pattern")

        # Look up best practices for API design
        search_memory(query="REST API authentication best practices")

        # Find past analyses about similar topics
        search_memory(query="React performance optimization", memory_type="analysis_summary")

    Returns:
        Formatted string with relevant memory snippets and their relevance scores.

    """
    logger.info(
        "search_memory_called",
        query=query[:100],  # Truncate for logging
        memory_type=memory_type,
        limit=limit,
    )

    # Parse memory type filter
    memory_type_filter = None
    if memory_type != "all":
        try:
            memory_type_filter = MemoryType(memory_type)
        except ValueError:
            valid_types = ", ".join([t.value for t in MemoryType])
            return f"Invalid memory_type '{memory_type}'. Valid options: all, {valid_types}"

    # Create session and search
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            service = AgentMemoryService(session)
            results = await service.search(
                query=query,
                memory_type=memory_type_filter,
                limit=limit,
            )

            if not results:
                logger.info("search_memory_no_results", query=query[:100])
                return (
                    "No relevant memories found for your query. Try broadening your search terms."
                )

            # Format results for agent consumption
            output_lines = [f"Found {len(results)} relevant memories:\n"]
            for i, result in enumerate(results, 1):
                output_lines.append(
                    f"{i}. [{result.memory.memory_type}] "
                    f"(relevance: {result.similarity:.2f})\n"
                    f"   {result.memory.content}\n"
                )

            output = "\n".join(output_lines)
            logger.info(
                "search_memory_success",
                query=query[:100],
                results_count=len(results),
            )
            return output

        except Exception as e:
            logger.exception("search_memory_error", query=query[:100], error=str(e))
            return f"Error searching memories: {e!s}"


# Tool configuration for registry
MEMORY_TOOL_CONFIG = {
    "name": "search_memory",
    "description": "Search past analyses and findings for relevant context (RAG)",
    "server": "skillforge",  # Internal tool server
}


# List of all memory tools
MEMORY_TOOLS = [search_memory]
