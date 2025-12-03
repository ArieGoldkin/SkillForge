"""Specificity scoring and validation for agent outputs.

This module measures how specific and quantifiable agent outputs are by:
- Counting vague phrases (appropriate, suitable, fast, slow, several, many)
- Counting numeric values with units (ms, s, %, MB, GB, req/s, hours)
- Calculating a specificity score (0.0 to 1.0)
- Providing detailed breakdown for monitoring and improvement

Usage:
    from app.workflows.agents.validation.specificity_scorer import SpecificityScorer

    scorer = SpecificityScorer()
    result = scorer.score_output(agent_findings, agent_type="performance_analyst")

    if result.overall_score < 0.75:
        logger.warning(
            "low_specificity_output",
            agent_type=agent_type,
            score=result.overall_score,
            vague_phrases=result.vague_phrase_count,
        )
"""

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)

# Quality level thresholds for specificity scoring
QUALITY_EXCELLENT_THRESHOLD = 0.85
QUALITY_GOOD_THRESHOLD = 0.70
QUALITY_MODERATE_THRESHOLD = 0.50

# Scoring weights
WEIGHT_NUMERIC_COMPLIANCE = 0.50
WEIGHT_NUMERIC_DENSITY = 0.30
WEIGHT_VAGUE_PENALTY = 0.20

# Limits and thresholds
VAGUE_PENALTY_THRESHOLD = 5  # Max vague phrases before heavy penalty
DEFAULT_EXPECTED_NUMERIC_COUNT = 10
LOW_SPECIFICITY_WARNING_THRESHOLD = 0.60

# Quick reference limits
MAX_PREREQUISITES = 4
MAX_CRITICAL_COMMANDS = 6
MAX_FILES_TO_MODIFY = 10
MAX_GOTCHAS = 5


@dataclass
class VaguePhrase:
    """A vague phrase detected in output."""

    phrase: str
    pattern: str
    context: str  # Surrounding text for debugging


@dataclass
class NumericValue:
    """A numeric value with units detected in output."""

    value: str
    unit: str
    context: str


@dataclass
class SpecificityScore:
    """Comprehensive specificity scoring result."""

    overall_score: float  # 0.0-1.0
    numeric_field_compliance: float  # 0.0-1.0
    numeric_density: float  # 0.0-1.0
    vague_penalty: float  # 0.0-1.0

    # Counts
    vague_phrase_count: int
    numeric_value_count: int
    expected_numeric_count: int

    # Details for debugging
    vague_phrases: list[VaguePhrase] = field(default_factory=list)
    numeric_values: list[NumericValue] = field(default_factory=list)

    # Quality classification
    quality_level: str = "unknown"  # poor, moderate, good, excellent

    def __post_init__(self) -> None:
        """Calculate quality level based on overall score."""
        if self.overall_score >= QUALITY_EXCELLENT_THRESHOLD:
            self.quality_level = "excellent"
        elif self.overall_score >= QUALITY_GOOD_THRESHOLD:
            self.quality_level = "good"
        elif self.overall_score >= QUALITY_MODERATE_THRESHOLD:
            self.quality_level = "moderate"
        else:
            self.quality_level = "poor"


class SpecificityScorer:
    """Scorer for measuring specificity of agent outputs.

    Detects vague phrases and numeric values to calculate a specificity score.
    Higher scores indicate more concrete, actionable outputs.
    """

    # Forbidden vague phrases with regex patterns
    VAGUE_PATTERNS: ClassVar[dict[str, str]] = {
        "qualitative_adjectives": r"\b(appropriate|suitable|reasonable|proper|adequate)\b",
        "relative_terms": r"\b(fast|slow|high|low|large|small|big|tiny)\b(?!\s*[:\-]?\s*\d)",
        "improvement_verbs": r"\b(improve|optimize|enhance|better|increase|decrease)\b(?!.*\d)",
        "quantity_vague": r"\b(several|many|few|some|numerous|various)\b",
        "approximations": r"\b(around|approximately|roughly|about)\b(?!\s*[~]?\d)",
        "intensifiers": r"\b(very|quite|rather|fairly|pretty|somewhat)\b",
        "modal_hedging": r"\b(might|could|should|would|may)\s+(be|help|improve)",
    }

    # Numeric value patterns (values WITH units)
    NUMERIC_PATTERNS: ClassVar[dict[str, str]] = {
        # Time units
        "time_ms": r"\d+[\d,.]*(ms|milliseconds?)\b",
        "time_s": r"\d+[\d,.]*\s*(s|sec|seconds?)\b",
        "time_min": r"\d+[\d,.]*\s*(min|mins|minutes?)\b",
        "time_hours": r"\d+[\d,.]*\s*(h|hr|hrs|hours?)\b",
        "time_days": r"\d+[\d,.]*\s*(d|days?)\b",
        # Throughput
        "throughput": r"\d+[\d,.]*\s*(req/s|req/sec|rps|ops/s|qps)\b",
        # Memory/Storage
        "memory_kb": r"\d+[\d,.]*\s*(KB|kB|kilobytes?)\b",
        "memory_mb": r"\d+[\d,.]*\s*(MB|megabytes?)\b",
        "memory_gb": r"\d+[\d,.]*\s*(GB|gigabytes?)\b",
        "memory_tb": r"\d+[\d,.]*\s*(TB|terabytes?)\b",
        # Percentage
        "percentage": r"\d+[\d,.]*\s*%",
        # Comparisons
        "comparison": r"[<>≤≥]\s*\d+[\d,.]*",
        # Ranges (hyphen or en-dash)
        "range": r"\d+[\d,.]*\s*[-\u2013]\s*\d+[\d,.]*",
        # Estimates with tilde
        "estimate": r"~\s*\d+[\d,.]*",
        # Version numbers
        "version": r"\d+\.\d+\.\d+",
        # CVE/CVSS scores
        "cve": r"CVE-\d{4}-\d+",
        "cvss": r"CVSS\s+\d+\.\d+",
        # Counts with units
        "count": r"\d+\s*(users?|requests?|instances?|connections?|queries?)\b",
    }

    # Agent-specific field expectations
    AGENT_FIELD_EXPECTATIONS: ClassVar[dict[str, dict[str, list[str]]]] = {
        "performance_analyst": {
            "numeric_fields": ["current_value", "target_value"],
            "list_fields": ["performance_metrics"],
        },
        "implementation_planner": {
            "numeric_fields": ["estimated_time", "duration_minutes"],
            "list_fields": ["steps", "prerequisites"],
        },
        "security_auditor": {
            "numeric_fields": ["cvss_score", "remediation_effort_hours"],
            "list_fields": ["security_risks"],
        },
        "dependency_mapper": {
            "numeric_fields": ["version"],
            "list_fields": ["dependencies", "version_constraints"],
        },
    }

    def __init__(self) -> None:
        """Initialize the specificity scorer."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self._compiled_vague = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.VAGUE_PATTERNS.items()
        }
        self._compiled_numeric = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.NUMERIC_PATTERNS.items()
        }

    def score_output(
        self,
        agent_output: dict[str, Any],
        agent_type: str = "unknown",
    ) -> SpecificityScore:
        """Calculate comprehensive specificity score for agent output.

        Args:
            agent_output: Agent findings dictionary
            agent_type: Type of agent (for agent-specific scoring)

        Returns:
            SpecificityScore with overall score and detailed breakdown

        """
        output_str = self._flatten_output(agent_output)

        # Detect vague phrases
        vague_phrases = self._detect_vague_phrases(output_str)
        vague_count = len(vague_phrases)

        # Detect numeric values
        numeric_values = self._detect_numeric_values(output_str)
        numeric_count = len(numeric_values)

        # Calculate expected numeric count based on agent type
        expected_numeric_count = self._get_expected_numeric_count(agent_type, agent_output)

        # Calculate component scores
        numeric_field_compliance = self._check_numeric_field_compliance(agent_output, agent_type)

        # Numeric density: ratio of actual to expected
        numeric_density = (
            min(1.0, numeric_count / expected_numeric_count) if expected_numeric_count > 0 else 0.0
        )

        # Vague phrase penalty: more vague phrases = lower score
        vague_penalty = max(0.0, 1.0 - (vague_count / VAGUE_PENALTY_THRESHOLD))

        # Overall score: weighted combination
        # - 50% weight: numeric field compliance (fields that MUST have numbers)
        # - 30% weight: numeric density (overall numeric value richness)
        # - 20% weight: vague phrase penalty (avoid vague language)
        overall_score = (
            WEIGHT_NUMERIC_COMPLIANCE * numeric_field_compliance
            + WEIGHT_NUMERIC_DENSITY * numeric_density
            + WEIGHT_VAGUE_PENALTY * vague_penalty
        )

        result = SpecificityScore(
            overall_score=round(overall_score, 3),
            numeric_field_compliance=round(numeric_field_compliance, 3),
            numeric_density=round(numeric_density, 3),
            vague_penalty=round(vague_penalty, 3),
            vague_phrase_count=vague_count,
            numeric_value_count=numeric_count,
            expected_numeric_count=expected_numeric_count,
            vague_phrases=vague_phrases,
            numeric_values=numeric_values,
        )

        # Log if score is concerning
        if result.overall_score < LOW_SPECIFICITY_WARNING_THRESHOLD:
            logger.warning(
                "low_specificity_detected",
                agent_type=agent_type,
                overall_score=result.overall_score,
                quality_level=result.quality_level,
                vague_count=vague_count,
                numeric_count=numeric_count,
                expected_numeric_count=expected_numeric_count,
            )

        return result

    def _flatten_output(self, data: Any, parent_key: str = "") -> str:
        """Flatten nested dict/list structure into searchable string.

        Args:
            data: Data to flatten
            parent_key: Parent key for nested structures

        Returns:
            Flattened string representation

        """
        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                parts.append(f"{new_key}: {self._flatten_output(value, new_key)}")
            return " | ".join(parts)
        elif isinstance(data, list):
            return " | ".join(self._flatten_output(item, parent_key) for item in data)
        else:
            return str(data)

    def _detect_vague_phrases(self, text: str) -> list[VaguePhrase]:
        """Detect vague phrases in text.

        Args:
            text: Text to search

        Returns:
            List of detected vague phrases with context

        """
        vague_phrases = []

        for pattern_name, compiled_pattern in self._compiled_vague.items():
            for match in compiled_pattern.finditer(text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]

                vague_phrases.append(
                    VaguePhrase(
                        phrase=match.group(),
                        pattern=pattern_name,
                        context=context,
                    )
                )

        return vague_phrases

    def _detect_numeric_values(self, text: str) -> list[NumericValue]:
        """Detect numeric values with units in text.

        Args:
            text: Text to search

        Returns:
            List of detected numeric values with context

        """
        numeric_values = []

        for _pattern_name, compiled_pattern in self._compiled_numeric.items():
            for match in compiled_pattern.finditer(text):
                # Extract value and unit
                matched_text = match.group()
                # Parse value and unit from matched text
                value_match = re.search(r"\d+[\d,.]*", matched_text)
                value = value_match.group() if value_match else ""

                # Extract unit (everything after the number)
                unit = matched_text.replace(value, "").strip()

                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]

                numeric_values.append(
                    NumericValue(
                        value=value,
                        unit=unit,
                        context=context,
                    )
                )

        return numeric_values

    def _get_expected_numeric_count(
        self,
        agent_type: str,
        agent_output: dict[str, Any],
    ) -> int:
        """Calculate expected number of numeric values based on agent type.

        Args:
            agent_type: Type of agent
            agent_output: Agent output dictionary

        Returns:
            Expected count of numeric values

        """
        # Base expectation: 10 numeric values
        base_count = 10

        # Adjust based on agent type and content size
        if agent_type == "performance_analyst":
            # Performance metrics should have 2 numeric values each (current, target)
            metrics = agent_output.get("performance_metrics", [])
            return len(metrics) * 2 + 5  # +5 for other fields

        elif agent_type == "implementation_planner":
            # Steps should have time estimates
            steps = agent_output.get("steps", [])
            return len(steps) + 3  # +3 for total time and other estimates

        elif agent_type == "security_auditor":
            # Security risks should have CVSS scores
            risks = agent_output.get("security_risks", [])
            return len(risks) + 5  # +5 for remediation times

        elif agent_type == "dependency_mapper":
            # Dependencies should have version numbers
            deps = agent_output.get("dependencies", [])
            return len(deps) + 3

        # Default for other agents
        return base_count

    def _check_numeric_field_compliance(
        self,
        agent_output: dict[str, Any],
        agent_type: str,
    ) -> float:
        """Check if fields that should have numeric values actually do.

        Args:
            agent_output: Agent output dictionary
            agent_type: Type of agent

        Returns:
            Compliance score (0.0-1.0)

        """
        expectations = self.AGENT_FIELD_EXPECTATIONS.get(agent_type)
        if not expectations:
            # No specific expectations - check for generic numeric values
            return 0.8  # Assume moderate compliance if we can't check specifics

        compliant = 0
        total = 0

        # Check numeric fields in list items
        list_fields = expectations.get("list_fields", [])
        numeric_fields = expectations.get("numeric_fields", [])

        for list_field in list_fields:
            items = agent_output.get(list_field, [])
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                for field_name in numeric_fields:
                    if field_name not in item:
                        continue

                    value = str(item[field_name])
                    total += 1

                    # Check if value contains number with unit
                    if self._has_numeric_with_unit(value):
                        compliant += 1

        # Check numeric fields at top level
        for field_name in numeric_fields:
            if field_name in agent_output:
                value = str(agent_output[field_name])
                total += 1

                if self._has_numeric_with_unit(value):
                    compliant += 1

        # Return compliance ratio
        return compliant / total if total > 0 else 1.0

    def _has_numeric_with_unit(self, text: str) -> bool:
        """Check if text contains a numeric value with units.

        Args:
            text: Text to check

        Returns:
            True if numeric value with unit found

        """
        # Check against all numeric patterns
        for compiled_pattern in self._compiled_numeric.values():
            if compiled_pattern.search(text):
                return True
        return False

    def get_detailed_report(self, score: SpecificityScore) -> str:
        """Generate detailed human-readable report.

        Args:
            score: SpecificityScore result

        Returns:
            Formatted report string

        """
        report_parts = [
            "=== Specificity Score Report ===",
            f"Overall Score: {score.overall_score:.3f} ({score.quality_level.upper()})",
            "",
            "Component Scores:",
            f"  - Numeric Field Compliance: {score.numeric_field_compliance:.3f}",
            f"  - Numeric Density: {score.numeric_density:.3f}",
            f"  - Vague Penalty: {score.vague_penalty:.3f}",
            "",
            "Counts:",
            f"  - Numeric Values: {score.numeric_value_count} (expected: {score.expected_numeric_count})",
            f"  - Vague Phrases: {score.vague_phrase_count}",
        ]

        if score.vague_phrases:
            report_parts.append("")
            report_parts.append(f"Vague Phrases Detected ({len(score.vague_phrases)}):")
            for i, vague in enumerate(score.vague_phrases[:5], 1):  # Show first 5
                report_parts.append(f"  {i}. '{vague.phrase}' ({vague.pattern})")
                report_parts.append(f"     Context: ...{vague.context}...")

        if score.numeric_values:
            report_parts.append("")
            report_parts.append(f"Numeric Values Detected ({len(score.numeric_values)}):")
            for i, numeric in enumerate(score.numeric_values[:5], 1):  # Show first 5
                report_parts.append(f"  {i}. {numeric.value}{numeric.unit}")

        return "\n".join(report_parts)


# Convenience functions for common use cases


def score_agent_output(
    agent_output: dict[str, Any],
    agent_type: str = "unknown",
) -> SpecificityScore:
    """Score agent output for specificity (convenience function).

    Args:
        agent_output: Agent findings dictionary
        agent_type: Type of agent

    Returns:
        SpecificityScore result

    """
    scorer = SpecificityScorer()
    return scorer.score_output(agent_output, agent_type)


def validate_specificity_threshold(
    agent_output: dict[str, Any],
    agent_type: str,
    threshold: float = 0.70,
) -> tuple[bool, SpecificityScore]:
    """Validate that agent output meets specificity threshold.

    Args:
        agent_output: Agent findings dictionary
        agent_type: Type of agent
        threshold: Minimum acceptable score (default: 0.70)

    Returns:
        Tuple of (passes_threshold, score)

    """
    score = score_agent_output(agent_output, agent_type)
    passes = score.overall_score >= threshold
    return passes, score
