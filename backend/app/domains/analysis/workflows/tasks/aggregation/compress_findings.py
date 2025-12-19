"""Finding compression for multi-phase synthesis.

Compresses each agent's verbose findings into essential summaries
to reduce token usage in synthesis prompts.

Phase 0 Implementation: Compresses 50K tokens from 8 agents to ~8-16K tokens
(1-2K per agent) using fast LLM-based summarization.
"""

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable

logger = get_logger(__name__)
settings = get_settings()

# Issue #299-304: Increased limits to preserve analytical depth for synthesis
# Previous limits (200 chars) were too aggressive, causing findings to be
# over-compressed, which resulted in shallow synthesis and low depth scores.
# These limits apply during finding compression before synthesis.
MAX_LIST_ITEMS = 10
MAX_STRING_LENGTH = 500  # Increased from 200 to preserve detail
MAX_VALUE_LENGTH = 500  # Increased from 200 to preserve detail


class CompressedFinding(BaseModel):
    """Compressed summary of an agent's findings."""

    agent_name: str
    key_insights: list[str] = Field(description="3-5 most important findings")
    confidence: float = Field(ge=0.0, le=1.0)
    data_quality: str = Field(description="high/medium/low")
    critical_warnings: list[str] = Field(default_factory=list)
    relevant_code_snippets: list[str] = Field(default_factory=list, max_length=3)


COMPRESSION_SYSTEM_PROMPT = """You are summarizing agent analysis findings for synthesis.

Your job is to extract ONLY the essential information that will be useful for
creating a comprehensive technical artifact.

Extract these fields:
1. key_insights: 3-5 bullet points - the most important findings (be specific, not vague)
2. confidence: 0.0-1.0 score - how confident is this analysis
3. data_quality: "high", "medium", or "low" - quality of source data
4. critical_warnings: Any blockers, security issues, or major concerns
5. relevant_code_snippets: Max 3 most relevant code examples (if any exist)

Be extremely concise. Focus on actionable insights, not filler.
Total output should be under 500 words per agent.

YOU MUST respond with a valid CompressedFinding object."""


def build_compression_user_prompt(agent_name: str, finding: dict[str, Any]) -> str:
    """Build user prompt for compressing a single agent's finding.

    Args:
        agent_name: Name of the agent
        finding: The agent's complete finding dictionary

    Returns:
        Formatted prompt string

    """
    # Extract the core findings data
    findings_data = finding.get("findings", {})
    confidence_score = finding.get("confidence_score", 0.5)
    data_availability = finding.get("data_availability", "unknown")

    # Format findings for compression
    findings_str = _format_findings_for_compression(findings_data)

    return f"""Agent: {agent_name}
Confidence Score: {confidence_score}
Data Availability: {data_availability}

Agent Findings:
{findings_str}

Extract the essential information into a CompressedFinding object.
Focus on what's actionable and specific - avoid filler words."""


def _format_findings_for_compression(findings_data: Any) -> str:
    """Format findings data into a string for compression.

    Args:
        findings_data: The findings data (dict, list, or other)

    Returns:
        Formatted string representation

    """
    if not findings_data:
        return "No findings available"

    if isinstance(findings_data, dict):
        # Format dict as key-value pairs
        lines = []
        for key, value in findings_data.items():
            if isinstance(value, (list, dict)):
                # Nested structures - show count
                if isinstance(value, list):
                    lines.append(f"{key}: {len(value)} items")
                    # Show first 2 items as examples
                    for item in value[:2]:
                        lines.append(f"  - {_format_value(item)}")
                else:
                    lines.append(f"{key}: {_format_value(value)}")
            else:
                lines.append(f"{key}: {_format_value(value)}")
        return "\n".join(lines)

    if isinstance(findings_data, list):
        # Format list as numbered items
        lines = []
        for i, item in enumerate(findings_data[:MAX_LIST_ITEMS]):
            lines.append(f"{i + 1}. {_format_value(item)}")
        if len(findings_data) > MAX_LIST_ITEMS:
            lines.append(f"... and {len(findings_data) - MAX_LIST_ITEMS} more items")
        return "\n".join(lines)

    # Fallback: convert to string
    return str(findings_data)[:2000]


def _format_value(value: Any) -> str:
    """Format a single value for display.

    Args:
        value: Any value to format

    Returns:
        Formatted string (truncated if too long)

    """
    if isinstance(value, dict):
        # Show dict keys
        return f"{{{', '.join(str(k) for k in list(value.keys())[:5])}}}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    value_str = str(value)
    # Truncate long strings
    if len(value_str) > MAX_VALUE_LENGTH:
        return value_str[: MAX_VALUE_LENGTH - 3] + "..."
    return value_str


@robust_traceable(
    name="compress_single_finding",
    run_type="llm",
    tags=["compression", "finding", "llm_call"],
    metadata={"service": "finding_compression"},
)
async def compress_single_finding(
    agent_name: str,
    finding: dict[str, Any],
    llm: Any,
    analysis_id: str,
) -> CompressedFinding:
    """Compress a single agent's finding using LLM summarization.

    Args:
        agent_name: Name of the agent
        finding: The agent's complete finding dictionary
        llm: LLM instance (with structured output bound)
        analysis_id: UUID of the analysis (for logging)

    Returns:
        CompressedFinding object with summarized data

    Raises:
        Exception: If compression fails

    """
    logger.debug(
        "finding_compression_started",
        agent_name=agent_name,
        analysis_id=analysis_id,
    )

    # Build compression prompt
    user_prompt = build_compression_user_prompt(agent_name, finding)

    # Issue #299-304: Fix - llm.with_structured_output() expects messages directly,
    # NOT wrapped in {"messages": [...]} dict format. Use HumanMessage/SystemMessage.
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=COMPRESSION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    # Invoke LLM directly with asyncio.timeout (30s for compression - should be fast)
    # Note: We bypass invoke_agent because llm.with_structured_output() expects
    # direct message input, not the agent-style {"messages": [...]} format
    async with asyncio.timeout(30.0):
        result = await llm.ainvoke(messages)

    # Extract structured response
    # The LLM has structured output bound, so result should be CompressedFinding
    # Cast result to dict for Pydantic model construction
    if isinstance(result, dict):
        # Type-safe extraction from dict
        key_insights_raw = result.get("key_insights", [])
        key_insights = (
            [str(x) for x in key_insights_raw] if isinstance(key_insights_raw, list) else []
        )

        warnings_raw = result.get("critical_warnings", [])
        warnings = [str(x) for x in warnings_raw] if isinstance(warnings_raw, list) else []

        snippets_raw = result.get("relevant_code_snippets", [])
        snippets = [str(x) for x in snippets_raw] if isinstance(snippets_raw, list) else []

        confidence_raw = result.get("confidence", 0.5)
        confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else 0.5

        compressed = CompressedFinding(
            agent_name=str(result.get("agent_name", agent_name)),
            key_insights=key_insights,
            confidence=confidence,
            data_quality=str(result.get("data_quality", "low")),
            critical_warnings=warnings,
            relevant_code_snippets=snippets,
        )
    else:
        # Already a CompressedFinding from structured output
        compressed = result  # type: ignore[assignment]

    logger.info(
        "finding_compression_complete",
        agent_name=agent_name,
        analysis_id=analysis_id,
        insights_count=len(compressed.key_insights),
        warnings_count=len(compressed.critical_warnings),
        snippets_count=len(compressed.relevant_code_snippets),
    )

    return compressed


@robust_traceable(
    name="compress_all_findings",
    run_type="chain",
    tags=["compression", "aggregation", "parallel"],
    metadata={"service": "finding_compression"},
)
async def compress_all_findings(
    agent_findings: dict[str, dict[str, Any]],
    analysis_id: str,
) -> list[CompressedFinding]:
    """Compress all agent findings in parallel using fast LLM.

    Phase 0 Implementation: Uses gemini-2.0-flash-lite for fast, cheap compression.
    Runs all 8 compressions in parallel to minimize latency.

    Args:
        agent_findings: Dictionary mapping agent names to their findings
        analysis_id: UUID of the analysis (for logging)

    Returns:
        List of CompressedFinding objects (one per agent)

    Note:
        If compression fails for one agent, returns a minimal fallback for that agent.
        The overall compression process never fails - always returns something.

    """
    if not agent_findings:
        logger.warning("compress_all_findings_no_findings", analysis_id=analysis_id)
        return []

    logger.info(
        "compress_all_findings_started",
        analysis_id=analysis_id,
        agent_count=len(agent_findings),
    )

    # Create fast LLM for compression (use gemini-2.0-flash-lite or fallback)
    # This is a very cheap model optimized for speed
    compression_model = "gemini-2.0-flash-lite"

    try:
        llm = get_chat_model(config={"configurable": {"model": compression_model}})
        # LangChain 1.2.x: Use strict mode for exact schema compliance
        # Compressed findings feed into synthesis - invalid compression breaks pipeline
        llm_with_structure = llm.with_structured_output(CompressedFinding, strict=True)
    except Exception as e:  # noqa: BLE001 - Must catch all model initialization errors
        # If gemini-2.0-flash-lite fails, fall back to the settings fallback model
        logger.warning(
            "compression_model_fallback",
            analysis_id=analysis_id,
            primary_model=compression_model,
            fallback_model=settings.LLM_FALLBACK_MODEL,
            error=str(e),
        )
        llm = get_chat_model(config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}})
        # LangChain 1.2.x: Use strict mode for exact schema compliance
        llm_with_structure = llm.with_structured_output(CompressedFinding, strict=True)

    # Create compression tasks for all agents
    tasks = []
    agent_names = []
    for agent_name, finding in agent_findings.items():
        agent_names.append(agent_name)
        task = compress_single_finding(
            agent_name=agent_name,
            finding=finding,
            llm=llm_with_structure,
            analysis_id=analysis_id,
        )
        tasks.append(task)

    # Run all compressions in parallel with error handling
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle failures
    compressed_findings: list[CompressedFinding] = []
    for i, result in enumerate(results):
        agent_name = agent_names[i]
        if isinstance(result, Exception):
            # Compression failed for this agent - create fallback
            logger.error(
                "finding_compression_failed",
                agent_name=agent_name,
                analysis_id=analysis_id,
                error=str(result),
                error_type=type(result).__name__,
                fallback="using_minimal_summary",
            )
            # Create minimal fallback
            original_finding = agent_findings[agent_name]
            fallback = _create_fallback_compressed_finding(agent_name, original_finding)
            compressed_findings.append(fallback)
        else:
            # Compression succeeded - result is CompressedFinding
            compressed_findings.append(result)  # type: ignore[arg-type]

    logger.info(
        "compress_all_findings_complete",
        analysis_id=analysis_id,
        agent_count=len(agent_findings),
        compressed_count=len(compressed_findings),
        failed_count=sum(1 for r in results if isinstance(r, Exception)),
    )

    return compressed_findings


def _create_fallback_compressed_finding(
    agent_name: str,
    finding: dict[str, Any],
) -> CompressedFinding:
    """Create a minimal fallback CompressedFinding when compression fails.

    Args:
        agent_name: Name of the agent
        finding: Original finding dictionary

    Returns:
        Minimal CompressedFinding with basic info extracted

    """
    findings_data = finding.get("findings", {})
    confidence_score = finding.get("confidence_score", 0.5)
    data_availability = finding.get("data_availability", "unknown")

    # Extract basic insights
    key_insights = [f"Analysis from {agent_name} agent"]

    # Try to extract some basic info from findings
    if isinstance(findings_data, dict):
        # Add top-level keys as insights
        for key, value in list(findings_data.items())[:3]:
            if isinstance(value, str) and len(value) < MAX_STRING_LENGTH:
                key_insights.append(f"{key}: {value}")
            elif isinstance(value, list):
                key_insights.append(f"{key}: {len(value)} items found")
            elif isinstance(value, dict):
                key_insights.append(f"{key}: {len(value)} fields")

    # Map data_availability to data_quality
    quality_map = {
        "sufficient": "high",
        "limited": "medium",
        "insufficient": "low",
        "unknown": "low",
    }
    data_quality = quality_map.get(data_availability, "low")

    return CompressedFinding(
        agent_name=agent_name,
        key_insights=key_insights[:5],  # Max 5
        confidence=float(confidence_score) if isinstance(confidence_score, (int, float)) else 0.5,
        data_quality=data_quality,
        critical_warnings=[],
        relevant_code_snippets=[],
    )
