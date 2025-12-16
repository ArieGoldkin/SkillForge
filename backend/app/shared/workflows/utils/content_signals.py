"""Content signal detection for intelligent agent routing.

This module detects WHAT'S IN the content (signals) rather than just
how long it is. This enables:
1. Routing only appropriate agents (don't ask security_auditor to analyze opinion piece)
2. Setting agent expectations (FULL_ANALYSIS vs OPPORTUNISTIC)
3. Honest synthesis that acknowledges coverage gaps

Issue #299-304: Graceful degradation for varying content sizes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class ContentGenre(Enum):
    """High-level content classification."""

    TUTORIAL = "tutorial"  # Step-by-step instructions
    REFERENCE = "reference"  # API docs, specifications
    OPINION = "opinion"  # Blog posts, think pieces
    RESEARCH = "research"  # Academic papers, surveys
    QUICKSTART = "quickstart"  # READMEs, getting started guides
    CHANGELOG = "changelog"  # Release notes, version history
    UNKNOWN = "unknown"


class DataAvailability(Enum):
    """Agent's assessment of data availability for its analysis type.

    Used by agents to honestly report what they found, not fail.
    """

    SUFFICIENT = "sufficient"  # Found all data needed for thorough analysis
    LIMITED = "limited"  # Found some data, analysis is partial
    INSUFFICIENT = "insufficient"  # No relevant data for this analysis type


class AgentExpectation(Enum):
    """Expected analysis depth based on content signals.

    Passed to agents so they know what's expected.
    """

    FULL_ANALYSIS = "full_analysis"  # Content has rich data for this agent
    PARTIAL = "partial"  # Content has some relevant data
    OPPORTUNISTIC = "opportunistic"  # Agent may find nothing (that's OK)


@dataclass
class ContentSignals:
    """Detected signals indicating what analysis is possible.

    These are boolean flags + a composite richness score.
    Detection takes < 50ms via regex patterns.
    """

    # Boolean signals - what's present in content
    has_code_patterns: bool = False  # Imports, functions, code blocks
    has_benchmarks: bool = False  # Performance numbers, latency, throughput
    has_security_patterns: bool = False  # Auth, encryption, vulnerabilities
    has_architecture: bool = False  # System components, diagrams, data flow
    has_dependencies: bool = False  # Package refs, requirements, imports
    has_comparisons: bool = False  # "vs", trade-offs, alternatives
    has_tutorials: bool = False  # Step-by-step, numbered instructions
    has_conceptual_only: bool = False  # Theory without implementation

    # Composite metrics
    content_richness_score: float = 0.0  # 0-10 based on signal density
    detected_genre: ContentGenre = ContentGenre.UNKNOWN
    word_count: int = 0
    char_count: int = 0

    # Agent expectations based on signals
    agent_expectations: dict[str, AgentExpectation] = field(default_factory=dict)

    def get_appropriate_agents(self) -> list[str]:
        """Return list of agents that should be routed based on signals."""
        appropriate = []

        # Always include these (can work with any content)
        appropriate.append("trend_validator")

        # Conditional based on signals
        if self.has_code_patterns or self.has_tutorials or self.has_architecture:
            appropriate.append("implementation_planner")

        if self.has_dependencies or self.has_code_patterns:
            appropriate.append("dependency_mapper")

        if self.has_security_patterns:
            appropriate.append("security_auditor")

        if self.has_benchmarks or self.has_code_patterns:
            appropriate.append("performance_analyst")

        if self.has_comparisons or self.has_architecture:
            appropriate.append("tech_comparator")

        if self.has_code_patterns or self.has_tutorials:
            appropriate.append("integration_feasibility")

        return appropriate

    def get_coverage_summary(self) -> str:
        """Return human-readable summary of what analysis is possible."""
        signals_present = []
        if self.has_code_patterns:
            signals_present.append("code examples")
        if self.has_benchmarks:
            signals_present.append("performance data")
        if self.has_security_patterns:
            signals_present.append("security considerations")
        if self.has_architecture:
            signals_present.append("architecture details")
        if self.has_dependencies:
            signals_present.append("dependency information")
        if self.has_comparisons:
            signals_present.append("technology comparisons")
        if self.has_tutorials:
            signals_present.append("implementation steps")

        if not signals_present:
            return "conceptual overview only"

        return ", ".join(signals_present)


# =============================================================================
# SIGNAL DETECTION PATTERNS
# =============================================================================

# Code patterns - imports, function defs, code blocks
CODE_PATTERNS = [
    r"```\w+",  # Fenced code blocks
    r"^import\s+\w+",  # Python imports
    r"^from\s+\w+\s+import",  # Python from imports
    r"def\s+\w+\s*\(",  # Function definitions
    r"class\s+\w+[:\(]",  # Class definitions
    r"function\s+\w+\s*\(",  # JavaScript functions
    r"const\s+\w+\s*=",  # JavaScript const
    r"async\s+(def|function)",  # Async definitions
    r"@\w+\s*(\(|$)",  # Decorators
    r"\bawait\s+\w+",  # Await expressions
]

# Benchmark/performance patterns
BENCHMARK_PATTERNS = [
    r"\d+\s*(ms|milliseconds?|seconds?|minutes?)",  # Time measurements
    r"\d+(\.\d+)?\s*(MB|GB|KB|bytes?)",  # Memory measurements
    r"\d+(\.\d+)?\s*(req|requests?|ops|operations?)\s*/\s*(s|sec|second)",  # Throughput
    r"latency|throughput|performance|benchmark",  # Performance keywords
    r"p\d{2,3}\s*[:=]?\s*\d+",  # Percentile metrics (p50, p99)
    r"\d+(\.\d+)?x\s+(faster|slower|improvement)",  # Comparison metrics
    r"(cpu|memory|disk)\s+usage",  # Resource usage
]

# Security patterns
SECURITY_PATTERNS = [
    r"auth(entication|orization)?",  # Auth patterns
    r"oauth|jwt|token|bearer",  # Token patterns
    r"encrypt(ion|ed)?|decrypt",  # Encryption
    r"vulnerabilit(y|ies)|cve-\d+",  # Vulnerabilities
    r"injection|xss|csrf|sqli",  # Attack patterns
    r"sanitiz(e|ation)|validat(e|ion)",  # Input validation
    r"https?://|ssl|tls|certificate",  # Transport security
    r"password|credential|secret|api[_-]?key",  # Secrets
    r"rbac|acl|permission|role",  # Access control
]

# Architecture patterns
ARCHITECTURE_PATTERNS = [
    r"(micro)?service|api\s+gateway",  # Service patterns
    r"database|postgres|mysql|mongodb|redis",  # Data stores
    r"queue|kafka|rabbitmq|pubsub",  # Messaging
    r"container|docker|kubernetes|k8s",  # Containerization
    r"load\s*balanc|replica|shard",  # Scaling patterns
    r"cache|cdn|edge",  # Caching patterns
    r"component|module|layer|tier",  # Architecture terms
    r"diagram|flowchart|sequence",  # Diagram references
    r"data\s*flow|architecture",  # Architecture discussions
]

# Dependency patterns
DEPENDENCY_PATTERNS = [
    r"pip\s+install|npm\s+install|yarn\s+add",  # Install commands
    r"requirements\.txt|package\.json|pyproject\.toml",  # Dependency files
    r"import\s+\w+|from\s+\w+",  # Import statements
    r"version\s*[=<>]+\s*[\d\.]+",  # Version constraints
    r"dependency|dependencies|prerequisite",  # Dependency keywords
    r"@\d+\.\d+|==\d+\.\d+",  # Version pinning
]

# Comparison patterns
COMPARISON_PATTERNS = [
    r"\bvs\.?\b|\bversus\b",  # vs/versus
    r"compar(e|ing|ison)",  # Compare words
    r"(better|worse)\s+than",  # Comparison phrases
    r"trade-?off|pro(s)?\s+(and|&)\s+con",  # Trade-off discussions
    r"alternative|instead\s+of",  # Alternatives
    r"(dis)?advantage",  # Advantages/disadvantages
    r"benchmark\s+results?|performance\s+comparison",  # Benchmark comparisons
]

# Tutorial patterns
TUTORIAL_PATTERNS = [
    r"step\s+\d+|step-by-step",  # Step instructions
    r"^\s*\d+\.\s+\w+",  # Numbered lists
    r"first,?\s+(we|you)|then,?\s+(we|you)|finally",  # Sequence words
    r"(let'?s|we'?ll)\s+(create|build|implement)",  # Tutorial language
    r"tutorial|guide|how\s+to|walkthrough",  # Tutorial keywords
    r"getting\s+started|quickstart",  # Getting started
    r"example|demo|sample",  # Example references
]


def detect_content_signals(content: str) -> ContentSignals:
    """Detect what types of analysis are possible from content.

    This is the main entry point. Returns ContentSignals with:
    - Boolean flags for each signal type
    - Content richness score (0-10)
    - Detected genre
    - Agent expectations mapping

    Performance: < 50ms for typical content via compiled regex.

    Args:
        content: Raw content string to analyze

    Returns:
        ContentSignals dataclass with all detected signals

    """
    if not content:
        return ContentSignals()

    content_lower = content.lower()
    word_count = len(content.split())
    char_count = len(content)

    # Detect each signal type
    has_code = _detect_patterns(content, CODE_PATTERNS, threshold=2)
    has_benchmarks = _detect_patterns(content_lower, BENCHMARK_PATTERNS, threshold=2)
    has_security = _detect_patterns(content_lower, SECURITY_PATTERNS, threshold=2)
    has_architecture = _detect_patterns(content_lower, ARCHITECTURE_PATTERNS, threshold=2)
    has_dependencies = _detect_patterns(content_lower, DEPENDENCY_PATTERNS, threshold=2)
    has_comparisons = _detect_patterns(content_lower, COMPARISON_PATTERNS, threshold=2)
    has_tutorials = _detect_patterns(content_lower, TUTORIAL_PATTERNS, threshold=2)

    # Conceptual only = no code, no tutorials, no benchmarks
    has_conceptual_only = not (has_code or has_tutorials or has_benchmarks)

    # Calculate richness score (0-10)
    signal_count = sum(
        [
            has_code,
            has_benchmarks,
            has_security,
            has_architecture,
            has_dependencies,
            has_comparisons,
            has_tutorials,
        ]
    )
    # Base score from signals (each worth ~1.4 points)
    richness_score = min(10.0, signal_count * 1.4)

    # Boost for longer content (max +2 points)
    word_count_threshold_high = 2000
    word_count_threshold_mid = 1000
    if word_count > word_count_threshold_high:
        richness_score = min(10.0, richness_score + 2.0)
    elif word_count > word_count_threshold_mid:
        richness_score = min(10.0, richness_score + 1.0)

    # Detect genre
    genre = _detect_genre(
        content_lower,
        has_code=has_code,
        has_tutorials=has_tutorials,
        has_benchmarks=has_benchmarks,
    )

    signals = ContentSignals(
        has_code_patterns=has_code,
        has_benchmarks=has_benchmarks,
        has_security_patterns=has_security,
        has_architecture=has_architecture,
        has_dependencies=has_dependencies,
        has_comparisons=has_comparisons,
        has_tutorials=has_tutorials,
        has_conceptual_only=has_conceptual_only,
        content_richness_score=round(richness_score, 1),
        detected_genre=genre,
        word_count=word_count,
        char_count=char_count,
    )

    # Set agent expectations based on signals
    signals.agent_expectations = _compute_agent_expectations(signals)

    logger.info(
        "content_signals_detected",
        word_count=word_count,
        char_count=char_count,
        richness_score=richness_score,
        genre=genre.value,
        has_code=has_code,
        has_benchmarks=has_benchmarks,
        has_security=has_security,
        has_architecture=has_architecture,
        has_tutorials=has_tutorials,
        appropriate_agents=signals.get_appropriate_agents(),
    )

    return signals


def _detect_patterns(content: str, patterns: list[str], threshold: int = 2) -> bool:
    """Check if content matches enough patterns.

    Args:
        content: Content to check
        patterns: List of regex patterns
        threshold: Minimum matches required

    Returns:
        True if matches >= threshold

    """
    matches = sum(1 for p in patterns if re.search(p, content, re.MULTILINE | re.IGNORECASE))
    return matches >= threshold


def _detect_genre(  # noqa: PLR0911
    content_lower: str,
    has_code: bool,
    has_tutorials: bool,
    has_benchmarks: bool,
) -> ContentGenre:
    """Detect content genre based on signals and keywords."""
    # Check for changelog patterns
    is_changelog_keywords = re.search(r"changelog|release\s+notes|what'?s\s+new", content_lower)
    is_changelog_versioned = re.search(r"##?\s*\[?\d+\.\d+", content_lower)
    if is_changelog_keywords and is_changelog_versioned:
        return ContentGenre.CHANGELOG

    # Tutorial = has steps + code
    if has_tutorials and has_code:
        return ContentGenre.TUTORIAL

    # Quickstart = short tutorial indicators
    if re.search(r"getting\s+started|quickstart|readme", content_lower):
        return ContentGenre.QUICKSTART

    # Research = academic patterns
    if re.search(r"abstract|conclusion|methodology|related\s+work|references", content_lower):
        return ContentGenre.RESEARCH

    # Reference = API docs, specs
    if re.search(r"api\s+reference|specification|endpoints?|parameters?", content_lower):
        return ContentGenre.REFERENCE

    # Opinion = blog indicators without technical depth
    is_opinion_keywords = re.search(r"i\s+think|in\s+my\s+(opinion|experience)|blog", content_lower)
    if not has_code and not has_benchmarks and is_opinion_keywords:
        return ContentGenre.OPINION

    return ContentGenre.UNKNOWN


def _compute_agent_expectations(signals: ContentSignals) -> dict[str, AgentExpectation]:  # noqa: PLR0912
    """Compute expectations for each agent based on signals.

    This tells agents what to expect so they can report honestly
    instead of "failing" when data isn't available.

    """
    expectations: dict[str, AgentExpectation] = {}

    # Security auditor
    if signals.has_security_patterns:
        # Content-aware: lower expectations for conceptual/research content
        if signals.has_conceptual_only and signals.detected_genre in [
            ContentGenre.OPINION,
            ContentGenre.RESEARCH,
        ]:
            expectations["security_auditor"] = AgentExpectation.PARTIAL
        else:
            expectations["security_auditor"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_code_patterns or signals.has_architecture:
        expectations["security_auditor"] = AgentExpectation.PARTIAL
    else:
        expectations["security_auditor"] = AgentExpectation.OPPORTUNISTIC

    # Performance analyst
    if signals.has_benchmarks:
        # Content-aware: lower expectations for conceptual/research content
        if signals.has_conceptual_only and signals.detected_genre in [
            ContentGenre.OPINION,
            ContentGenre.RESEARCH,
        ]:
            expectations["performance_analyst"] = AgentExpectation.PARTIAL
        else:
            expectations["performance_analyst"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_code_patterns:
        expectations["performance_analyst"] = AgentExpectation.PARTIAL
    else:
        expectations["performance_analyst"] = AgentExpectation.OPPORTUNISTIC

    # Implementation planner
    if signals.has_code_patterns and signals.has_tutorials:
        expectations["implementation_planner"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_code_patterns or signals.has_tutorials or signals.has_architecture:
        expectations["implementation_planner"] = AgentExpectation.PARTIAL
    else:
        expectations["implementation_planner"] = AgentExpectation.OPPORTUNISTIC

    # Tech comparator
    if signals.has_comparisons:
        expectations["tech_comparator"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_architecture:
        expectations["tech_comparator"] = AgentExpectation.PARTIAL
    else:
        expectations["tech_comparator"] = AgentExpectation.OPPORTUNISTIC

    # Dependency mapper
    if signals.has_dependencies:
        expectations["dependency_mapper"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_code_patterns:
        expectations["dependency_mapper"] = AgentExpectation.PARTIAL
    else:
        expectations["dependency_mapper"] = AgentExpectation.OPPORTUNISTIC

    # Trend validator - always FULL_ANALYSIS (can analyze any content type)
    expectations["trend_validator"] = AgentExpectation.FULL_ANALYSIS

    # Integration feasibility
    if signals.has_code_patterns and signals.has_architecture:
        expectations["integration_feasibility"] = AgentExpectation.FULL_ANALYSIS
    elif signals.has_code_patterns or signals.has_tutorials:
        expectations["integration_feasibility"] = AgentExpectation.PARTIAL
    else:
        expectations["integration_feasibility"] = AgentExpectation.OPPORTUNISTIC

    return expectations


def should_skip_agent(agent_name: str, signals: ContentSignals) -> tuple[bool, str]:
    """Determine if an agent should be skipped entirely.

    Some agents should not run at all if there's zero relevant data.
    This is different from OPPORTUNISTIC (might find something).

    Args:
        agent_name: Name of the agent
        signals: Detected content signals

    Returns:
        Tuple of (should_skip, reason)

    """
    # Code quality critic needs actual code
    if agent_name == "code_quality_critic" and not signals.has_code_patterns:
        return True, "No code patterns detected for structural analysis"

    # Security auditor on pure opinion pieces
    if (
        agent_name == "security_auditor"
        and signals.has_conceptual_only
        and signals.detected_genre == ContentGenre.OPINION
    ):
        return True, "Opinion content without technical patterns"

    # Performance analyst on conceptual-only content
    if (
        agent_name == "performance_analyst"
        and signals.has_conceptual_only
        and not signals.has_architecture
    ):
        return True, "No performance-relevant patterns detected"

    return False, ""


# =============================================================================
# SPECIFICITY THRESHOLD ADJUSTMENT (Issue #299-304)
# =============================================================================

# Default specificity threshold
DEFAULT_SPECIFICITY_THRESHOLD = 0.70

# Adjusted thresholds by expectation level
THRESHOLD_BY_EXPECTATION = {
    AgentExpectation.FULL_ANALYSIS: 0.70,  # Standard threshold
    AgentExpectation.PARTIAL: 0.55,  # Reduced for partial data
    AgentExpectation.OPPORTUNISTIC: 0.45,  # Further reduced for opportunistic
}


def get_adjusted_specificity_threshold(
    agent_name: str,
    signals: ContentSignals,
) -> float:
    """Get content-aware specificity threshold for an agent.

    Issue #299-304: Adjust threshold based on what's expected for this agent
    given the content signals. Agents with OPPORTUNISTIC expectations get
    lower thresholds since they're expected to work with limited data.

    Args:
        agent_name: Name of the agent (e.g., "trend_validator")
        signals: Detected content signals

    Returns:
        Adjusted specificity threshold (0.0-1.0)

    Example:
        >>> signals = detect_content_signals("Simple concept discussion")
        >>> signals.has_conceptual_only
        True
        >>> get_adjusted_specificity_threshold("trend_validator", signals)
        0.7  # trend_validator always expects full analysis
        >>> get_adjusted_specificity_threshold("security_auditor", signals)
        0.45  # security_auditor is opportunistic for conceptual content

    """
    expectation = signals.agent_expectations.get(agent_name, AgentExpectation.OPPORTUNISTIC)

    return THRESHOLD_BY_EXPECTATION.get(expectation, DEFAULT_SPECIFICITY_THRESHOLD)


def get_threshold_for_expectation(expectation_str: str | None) -> float:
    """Get specificity threshold from expectation string.

    Simpler version that works with expectation strings stored in state.
    Use this when you have the expectation value from supervisor_decision.

    Args:
        expectation_str: Expectation value string (e.g., "full_analysis", "partial", "opportunistic")
            or None if not available.

    Returns:
        Adjusted specificity threshold (0.0-1.0)

    Example:
        >>> # From state: state["supervisor_decision"]["agent_expectations"]["trend_validator"]
        >>> get_threshold_for_expectation("full_analysis")
        0.7
        >>> get_threshold_for_expectation("opportunistic")
        0.45
        >>> get_threshold_for_expectation(None)  # Not found in state
        0.7  # Default to standard threshold

    """
    if expectation_str is None:
        return DEFAULT_SPECIFICITY_THRESHOLD

    try:
        expectation = AgentExpectation(expectation_str)
        return THRESHOLD_BY_EXPECTATION.get(expectation, DEFAULT_SPECIFICITY_THRESHOLD)
    except ValueError:
        # Invalid expectation string, use default
        return DEFAULT_SPECIFICITY_THRESHOLD
