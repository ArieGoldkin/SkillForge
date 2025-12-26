"""Context scoping for multi-agent workflows.

This module implements context scoping to reduce state size passed to agents.
Instead of passing the full AnalysisState (~50KB) to each agent, we pass only
the minimal fields each agent needs (typically 3-4 fields).

Reference: Issue #246 - Multi-Agent Context Scoping (Sprint 11 Context Engineering)
"""

from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.types import AgentFinding

logger = get_logger(__name__)


class ContextScope(BaseModel):
    """Configuration for what context to pass to an agent.

    Attributes:
        include: List of state fields to include (e.g., ["analysis_id", "content_ref"])
        exclude: List of state fields to explicitly exclude (applied after include)
        inject_memory: Whether to inject prior agent findings as narrative context
        max_content_tokens: Maximum tokens for content (for future content truncation)
        include_other_findings: Whether to include findings from other agents

    """

    include: list[str] = Field(
        default_factory=list,
        description="State fields to include in scoped context",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="State fields to exclude (applied after include)",
    )
    inject_memory: bool = Field(
        default=False,
        description="Inject prior agent findings as narrative",
    )
    max_content_tokens: int | None = Field(
        default=None,
        description="Max tokens for content (future use)",
    )
    include_other_findings: bool = Field(
        default=False,
        description="Include findings from other agents",
    )


class ScopedState(dict):
    """Minimal state passed to agents.

    This is a TypedDict-style dict with only the minimal fields needed.
    Each agent receives only what it needs to do its job.

    Typical fields:
        analysis_id: Unique identifier for this analysis
        content_ref: Lightweight reference to content (Handle Pattern)
        content_type: Type of content (article, video, repo)
        skill_level: User's experience level
        prior_context: Narrative summary of other agents' findings (optional)
        prior_memory: Formatted memory context from proactive recall (Issue #266)

    """


# Agent scope configurations
# Each agent specifies exactly which state fields it needs
#
# Issue #244: Handle Pattern Implementation
# - content_ref: Lightweight URI reference to content stored in ArtifactStore
# - Agents use has_content_available() to check content_ref availability
# - Runners load optimized sections via ArtifactStore when content_ref is present
# - raw_content NOT included: use content_ref exclusively (Issue #299-304)
AGENT_SCOPES: dict[str, ContextScope] = {
    "security_auditor": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #442: Need content_signals for research-aware thresholds
        inject_memory=True,
        include_other_findings=False,
    ),
    "tech_comparator": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #299-304: Need content_signals for comparison-aware thresholds
        inject_memory=True,
        include_other_findings=False,
    ),
    "implementation_planner": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #299-304: Need content_signals for comparison-aware thresholds
        inject_memory=True,
        include_other_findings=True,  # Planner benefits from other findings
    ),
    "code_quality_critic": ContextScope(
        include=["analysis_id", "content_ref", "content_type", "skill_level"],
        inject_memory=False,
        include_other_findings=False,
    ),
    "dependency_mapper": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #299-304: Need content_signals for comparison-aware thresholds
        inject_memory=False,
        include_other_findings=False,
    ),
    "practical_applicator": ContextScope(
        include=["analysis_id", "content_ref", "content_type", "skill_level"],
        inject_memory=True,
        include_other_findings=True,
    ),
    "learning_path_designer": ContextScope(
        include=["analysis_id", "content_ref", "content_type", "skill_level"],
        inject_memory=True,
        include_other_findings=True,
    ),
    "reporter": ContextScope(
        include=["analysis_id", "content_ref", "content_type", "skill_level"],
        inject_memory=False,
        include_other_findings=False,
    ),
    "performance_analyst": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #442: Need content_signals for research-aware thresholds
        inject_memory=False,
        include_other_findings=False,
    ),
    "trend_validator": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Issue #299-304: Need content_signals for comparison-aware thresholds
        inject_memory=False,
        include_other_findings=False,
    ),
    "integration_feasibility": ContextScope(
        include=["analysis_id", "content_ref", "content_type", "skill_level"],
        inject_memory=True,
        include_other_findings=True,
    ),
    # Tier 3 Research agents (Issue #501) - memory-enabled deep analysis
    "deep_researcher": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Extended research with 10+ queries
        inject_memory=True,
        include_other_findings=True,  # Needs context from Tier 1/2 agents
    ),
    "community_pulse": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
            "content_signals",
        ],  # Sentiment analysis from community sources
        inject_memory=True,
        include_other_findings=False,
    ),
    "knowledge_curator": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
        ],  # Connects to user's knowledge graph via PGVector
        inject_memory=True,
        include_other_findings=True,  # Needs all findings for connection mapping
    ),
    "learning_path_advisor": ContextScope(
        include=[
            "analysis_id",
            "content_ref",
            "content_type",
            "skill_level",
        ],  # Personalizes learning paths based on user preferences
        inject_memory=True,
        include_other_findings=True,  # Needs findings for learning sequence
    ),
}


def _resolve_scope(agent_type: str, scope: ContextScope | None) -> ContextScope:
    """Resolve scope configuration for an agent.

    Args:
        agent_type: Type of agent (e.g., "security_auditor")
        scope: Optional custom scope (uses AGENT_SCOPES[agent_type] if not provided)

    Returns:
        Resolved ContextScope configuration

    """
    if scope is None:
        if agent_type not in AGENT_SCOPES:
            logger.warning(
                "agent_scope_not_found",
                agent_type=agent_type,
                using_default=True,
            )
            # Default scope: minimal safe fields
            return ContextScope(
                include=["analysis_id", "content_ref", "content_type", "skill_level"]
            )
        return AGENT_SCOPES[agent_type]
    return scope


def _inject_prior_context(
    scoped_state: ScopedState,
    full_state: AnalysisState,
    agent_type: str,
    scope: ContextScope,
) -> None:
    """Inject prior context (memory/findings) into scoped state if requested.

    Args:
        scoped_state: Scoped state to inject into (modified in place)
        full_state: Full AnalysisState with all fields
        agent_type: Type of agent receiving the context
        scope: ContextScope configuration with injection flags

    """
    if scope.inject_memory or scope.include_other_findings:
        prior_context = translate_findings(
            full_state.get("agent_findings", []),
            agent_type,
            include_findings=scope.include_other_findings,
        )
        if prior_context:
            scoped_state["prior_context"] = prior_context


def _inject_supervisor_data(
    scoped_state: ScopedState,
    full_state: AnalysisState,
    agent_type: str,
    scope: ContextScope,
) -> None:
    """Inject supervisor decision data into scoped state.

    Injects agent expectations, coverage summary, and content signals based on
    supervisor_decision data in full_state.

    Args:
        scoped_state: Scoped state to inject into (modified in place)
        full_state: Full AnalysisState with supervisor_decision data
        agent_type: Type of agent receiving the context
        scope: ContextScope configuration

    """
    supervisor_decision = full_state.get("supervisor_decision", {})
    if not isinstance(supervisor_decision, dict):
        return

    # Inject agent expectation if available
    agent_expectations = supervisor_decision.get("agent_expectations", {})
    if isinstance(agent_expectations, dict) and agent_type in agent_expectations:
        scoped_state["agent_expectation"] = agent_expectations[agent_type]
        logger.debug(
            "agent_expectation_injected",
            agent_type=agent_type,
            expectation=agent_expectations[agent_type],
        )

    # Inject coverage summary and content_signals if needed
    content_signals = supervisor_decision.get("content_signals")
    if isinstance(content_signals, dict):
        coverage = content_signals.get("coverage_summary")
        if coverage:
            scoped_state["content_coverage"] = coverage
        # Issue #299-304: Inject full content_signals for comparison-aware thresholds
        if "content_signals" in scope.include:
            scoped_state["content_signals"] = content_signals


def build_scoped_context(
    full_state: AnalysisState,
    agent_type: str,
    scope: ContextScope | None = None,
) -> ScopedState:
    """Build minimal scoped context for an agent.

    Args:
        full_state: Full AnalysisState with all fields
        agent_type: Type of agent (e.g., "security_auditor")
        scope: Optional custom scope (uses AGENT_SCOPES[agent_type] if not provided)

    Returns:
        ScopedState with only the minimal fields needed by this agent

    Example:
        >>> full_state = {
        ...     "analysis_id": "abc-123",
        ...     "content_ref": {...},
        ...     "content_type": "article",
        ...     "skill_level": "intermediate",
        ...     "raw_content": "very large content...",  # NOT included
        ...     "extraction_metadata": {...},  # NOT included
        ...     "agent_findings": [...],  # NOT included
        ... }
        >>> scoped = build_scoped_context(full_state, "security_auditor")
        >>> scoped.keys()
        dict_keys(['analysis_id', 'content_ref', 'content_type', 'skill_level'])

    """
    # Resolve scope configuration
    scope = _resolve_scope(agent_type, scope)

    # Build scoped state with only included fields
    scoped_state = ScopedState()
    for field in scope.include:
        # Type narrowing: check if field exists in full_state
        value = full_state.get(field)
        if value is not None:
            scoped_state[field] = value

    # Apply exclusions
    for field in scope.exclude:
        scoped_state.pop(field, None)

    # Inject prior context if requested
    _inject_prior_context(scoped_state, full_state, agent_type, scope)

    # Inject supervisor decision data (expectations, coverage, content_signals)
    _inject_supervisor_data(scoped_state, full_state, agent_type, scope)

    # Calculate size reduction
    # Cast to dict for size estimation (AnalysisState is TypedDict)
    # ty can't infer dict() constructor on TypedDict
    original_size = _estimate_state_size(dict(full_state))  # type: ignore[arg-type]
    scoped_size = _estimate_state_size(scoped_state)
    reduction_pct = (
        ((original_size - scoped_size) / original_size * 100) if original_size > 0 else 0
    )

    logger.info(
        "context_scope_applied",
        agent_type=agent_type,
        original_size_bytes=original_size,
        scoped_size_bytes=scoped_size,
        reduction_percent=f"{reduction_pct:.1f}%",
        included_fields=list(scoped_state.keys()),
    )

    return scoped_state


def translate_findings(
    findings: list[AgentFinding],
    target_agent: str,
    include_findings: bool = True,
) -> str:
    r"""Translate other agents' findings into narrative context.

    Converts structured findings from other agents into a concise narrative
    that provides helpful context without overwhelming the target agent.

    Args:
        findings: List of agent findings from state
        target_agent: Agent type receiving the context
        include_findings: Whether to include detailed findings (vs just summary)

    Returns:
        Narrative string with prior context, or empty string if no findings

    Example:
        >>> findings = [
        ...     {
        ...         "agent_type": "tech_comparator",
        ...         "findings": {"technologies": ["React", "TypeScript"]},
        ...     }
        ... ]
        >>> translate_findings(findings, "security_auditor")
        "Prior Analysis Context:\\n\\n1. tech_comparator: Found 2 key insights\\n"

    """
    if not findings:
        return ""

    # Filter out findings from the same agent (avoid self-reference)
    other_findings = [f for f in findings if f.get("agent_type") != target_agent]

    if not other_findings:
        return ""

    narrative_parts = ["Prior Analysis Context:\n"]

    for idx, finding in enumerate(other_findings, 1):
        agent_type_obj = finding.get("agent_type", "unknown")
        finding_data_obj = finding.get("findings", {})

        # Type narrowing for mypy
        agent_type_str = str(agent_type_obj) if agent_type_obj else "unknown"
        finding_data_dict = finding_data_obj if isinstance(finding_data_obj, dict) else {}

        # Extract key metrics for summary
        num_items = _count_finding_items(finding_data_dict)

        if include_findings:
            # Include detailed summary
            summary = _summarize_finding(finding_data_dict, agent_type_str)
            narrative_parts.append(f"{idx}. {agent_type_str}: {summary}")
        else:
            # Just mention that analysis was done
            narrative_parts.append(
                f"{idx}. {agent_type_str}: Completed with {num_items} key insights"
            )

    return "\n".join(narrative_parts)


def _estimate_state_size(state: dict[str, Any]) -> int:
    """Estimate size of state in bytes.

    This is a rough estimate using string representation length.
    Good enough for logging size reduction metrics.

    Args:
        state: State dictionary to estimate

    Returns:
        Estimated size in bytes

    """
    try:
        # Use str representation as rough estimate
        return len(str(state).encode("utf-8"))
    except Exception:  # noqa: BLE001
        # If we can't estimate, return 0
        return 0


def _count_finding_items(finding_data: dict[str, object]) -> int:
    """Count the number of items in a finding.

    Args:
        finding_data: Findings dictionary from agent

    Returns:
        Count of top-level list items or dict keys

    """
    total = 0
    for value in finding_data.values():
        if isinstance(value, (list, dict)):
            total += len(value)
    return total


def _summarize_finding(finding_data: dict[str, object], _agent_type: str) -> str:
    """Create a one-line summary of a finding.

    Args:
        finding_data: Findings dictionary from agent
        agent_type: Type of agent that created the finding

    Returns:
        One-line summary string

    """
    # Extract first few keys for summary
    keys = list(finding_data.keys())[:3]
    if not keys:
        return "Completed analysis"

    # Count items in each key
    summaries = []
    for key in keys:
        value = finding_data.get(key)
        if isinstance(value, (list, dict)):
            summaries.append(f"{len(value)} {key}")
        else:
            summaries.append(key)

    return f"Found {', '.join(summaries)}"
