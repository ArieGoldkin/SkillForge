"""Per-agent output validation heuristics for self-correction.

Issue #507: Validates agent output quality before it leaves the agent,
enabling per-agent retry instead of full workflow retry at the quality gate.

Each validator implements agent-specific rules based on the schema requirements
and quality heuristics defined in the issue acceptance criteria.

Usage:
    from app.domains.analysis.workflows.agents.validation.output_validators import (
        get_validator,
        ValidationResult,
    )

    validator = get_validator("key_insights")
    if validator:
        result = validator.validate(agent_output)
        if not result.is_valid and result.retry_recommended:
            # Build correction prompt and retry
            ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.core.logging import get_logger

logger = get_logger(__name__)

# Validation thresholds
MIN_CONFIDENCE_SCORE = 0.3
MIN_DESCRIPTION_LENGTH = 50
MIN_VERDICT_LENGTH = 20
MAX_RETRYABLE_ISSUES = 3  # Maximum issues for retry to be recommended
MIN_AUDIENCE_NAME_LENGTH = 10
MIN_RELEVANCE_EXPLANATION_LENGTH = 20
MIN_ACTION_TEXT_LENGTH = 20
MIN_OUTCOME_LENGTH = 20
MIN_QUICK_WIN_LENGTH = 30
MIN_TECH_NAME_LENGTH = 2  # Minimum technology name length
MIN_SECURITY_DESCRIPTION_LENGTH = 50  # Minimum security risk description length

# Placeholder patterns to detect incomplete responses
PLACEHOLDER_PATTERNS: list[str] = [
    "todo",
    "placeholder",
    "tbd",
    "to be determined",
    "more details needed",
    "see above",
    "as mentioned",
    "[insert",
    "[add",
    "fill in",
    "example here",
    "your text here",
]

# Generic patterns that indicate low-quality output
GENERIC_PATTERNS: list[str] = [
    "it's good",
    "it works",
    "no issues",
    "nothing bad",
    "works well",
    "very useful",
    "highly recommended",
    "great tool",
]


@dataclass
class ValidationResult:
    """Result of output validation.

    Attributes:
        is_valid: Whether the output passes all validation checks
        issues: List of specific issues found during validation
        confidence: Confidence in the validation result (0.0-1.0)
        retry_recommended: Whether a retry might improve the output

    """

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    confidence: float = 0.8
    retry_recommended: bool = True

    def __post_init__(self) -> None:
        """Calculate retry recommendation based on issues."""
        # Only recommend retry if there are fixable issues (<=MAX_RETRYABLE_ISSUES)
        # More issues suggests fundamental problems
        if len(self.issues) > MAX_RETRYABLE_ISSUES:
            self.retry_recommended = False


class AgentOutputValidator(ABC):
    """Base class for agent-specific output validators.

    Each validator implements validation rules specific to an agent type,
    checking for completeness, quality, and adherence to schema requirements.
    """

    agent_type: ClassVar[str] = "unknown"

    @abstractmethod
    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate agent output and return result.

        Args:
            output: Agent findings dictionary (Pydantic model_dump() output)

        Returns:
            ValidationResult with validation status and issues

        """

    @abstractmethod
    def get_correction_hints(self) -> list[str]:
        """Get hints for the correction prompt.

        Returns:
            List of hints to guide the LLM in correcting its output

        """

    def _check_confidence_score(self, output: dict[str, Any], issues: list[str]) -> None:
        """Check if confidence score meets minimum threshold."""
        confidence = output.get("confidence_score", 1.0)
        if confidence < MIN_CONFIDENCE_SCORE:
            issues.append(f"Low confidence score ({confidence:.2f} < {MIN_CONFIDENCE_SCORE})")

    def _check_placeholder_text(self, text: str, field_name: str, issues: list[str]) -> bool:
        """Check for placeholder text in a field.

        Returns:
            True if placeholder found, False otherwise

        """
        text_lower = text.lower()
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in text_lower:
                issues.append(f"'{field_name}' contains placeholder text: '{pattern}'")
                return True
        return False

    def _check_generic_text(self, text: str, field_name: str, issues: list[str]) -> bool:
        """Check for generic/vague statements.

        Returns:
            True if generic pattern found, False otherwise

        """
        text_lower = text.lower()
        for pattern in GENERIC_PATTERNS:
            if pattern in text_lower:
                issues.append(f"'{field_name}' contains generic statement: '{pattern}'")
                return True
        return False


class KeyInsightsValidator(AgentOutputValidator):
    """Validator for key_insights agent outputs.

    Validation rules (from Issue #507):
    - >= 3 insights (schema enforces, but check for placeholder content)
    - No duplicate insight titles
    - Each insight has substantive "why it matters" content (50+ chars)
    - Insights reference specific content (not generic statements)
    """

    agent_type: ClassVar[str] = "key_insights"
    MIN_INSIGHTS = 3

    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate key_insights output."""
        issues: list[str] = []
        insights = output.get("insights", [])

        # Check count
        if len(insights) < self.MIN_INSIGHTS:
            issues.append(f"Only {len(insights)} insights, need >= {self.MIN_INSIGHTS}")

        # Check for duplicates
        titles = [i.get("title", "").lower().strip() for i in insights if isinstance(i, dict)]
        if len(titles) != len(set(titles)):
            issues.append("Duplicate insight titles detected")

        # Check each insight for quality
        for i, insight in enumerate(insights):
            if not isinstance(insight, dict):
                issues.append(f"Insight {i + 1} is not a valid object")
                continue

            title = insight.get("title", "")
            description = insight.get("description", "")

            # Check description length
            if len(description) < MIN_DESCRIPTION_LENGTH:
                issues.append(
                    f"Insight {i + 1} has insufficient description "
                    f"({len(description)} chars < {MIN_DESCRIPTION_LENGTH})"
                )

            # Check for placeholder/generic content
            self._check_placeholder_text(title, f"insight {i + 1} title", issues)
            self._check_placeholder_text(description, f"insight {i + 1} description", issues)
            self._check_generic_text(description, f"insight {i + 1} description", issues)

        # Check summary
        summary = output.get("summary", "")
        if len(summary) < MIN_DESCRIPTION_LENGTH:
            issues.append(f"Summary too short ({len(summary)} chars)")
        self._check_placeholder_text(summary, "summary", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for key_insights."""
        return [
            f"Provide at least {self.MIN_INSIGHTS} unique, non-overlapping insights",
            f"Each insight description must be substantive ({MIN_DESCRIPTION_LENGTH}+ chars)",
            "Reference specific details from the content, not generic statements",
            "Avoid placeholder phrases like 'TBD', 'to be determined', '[insert]'",
            "Each insight title should be unique and descriptive",
        ]


class ProsConsValidator(AgentOutputValidator):
    """Validator for pros_cons agent outputs.

    Validation rules:
    - >= 2 pros
    - >= 2 cons (or >= 1 per schema)
    - Verdict present and substantive (20+ chars)
    - No generic statements like "it's good"
    """

    agent_type: ClassVar[str] = "pros_cons"
    MIN_PROS = 2
    MIN_CONS = 1  # Schema allows 1, but 2 is better

    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate pros_cons output."""
        issues: list[str] = []

        pros = output.get("pros", [])
        cons = output.get("cons", [])
        verdict = output.get("verdict", "")

        # Check counts
        if len(pros) < self.MIN_PROS:
            issues.append(f"Only {len(pros)} pros, need >= {self.MIN_PROS}")
        if len(cons) < self.MIN_CONS:
            issues.append(f"Only {len(cons)} cons, need >= {self.MIN_CONS}")

        # Check verdict
        if not verdict or len(verdict.strip()) < MIN_VERDICT_LENGTH:
            issues.append(f"Verdict is missing or too short (< {MIN_VERDICT_LENGTH} chars)")
        else:
            self._check_placeholder_text(verdict, "verdict", issues)

        # Check for generic pros/cons
        for i, pro in enumerate(pros):
            if isinstance(pro, str):
                self._check_generic_text(pro, f"pro {i + 1}", issues)
                self._check_placeholder_text(pro, f"pro {i + 1}", issues)

        for i, con in enumerate(cons):
            if isinstance(con, str):
                self._check_generic_text(con, f"con {i + 1}", issues)
                self._check_placeholder_text(con, f"con {i + 1}", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for pros_cons."""
        return [
            f"Provide at least {self.MIN_PROS} specific pros with concrete benefits",
            f"Provide at least {self.MIN_CONS} specific cons with concrete limitations",
            f"Include a substantive verdict ({MIN_VERDICT_LENGTH}+ chars) summarizing trade-offs",
            "Avoid generic statements like 'it's good' or 'works well'",
            "Cite specific features, metrics, or examples from the content",
        ]


class AudienceFitValidator(AgentOutputValidator):
    """Validator for audience_fit agent outputs.

    Validation rules:
    - >= 1 audience defined (primary_audience required)
    - Prerequisites list exists and has items
    - Primary audience has substantive relevance explanation
    """

    agent_type: ClassVar[str] = "audience_fit"
    MIN_PREREQUISITES = 1

    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate audience_fit output."""
        issues: list[str] = []

        primary_audience = output.get("primary_audience")
        prerequisites = output.get("prerequisites", [])

        # Check primary audience
        if not primary_audience or not isinstance(primary_audience, dict):
            issues.append("Primary audience is missing or invalid")
        else:
            name = primary_audience.get("name", "")
            why_relevant = primary_audience.get("why_relevant", "")

            if not name or len(name) < MIN_AUDIENCE_NAME_LENGTH:
                issues.append("Primary audience name is missing or too short")
            if not why_relevant or len(why_relevant) < MIN_RELEVANCE_EXPLANATION_LENGTH:
                issues.append("Primary audience 'why_relevant' explanation is missing or too short")

            self._check_placeholder_text(name, "primary_audience.name", issues)
            self._check_placeholder_text(why_relevant, "primary_audience.why_relevant", issues)

        # Check prerequisites
        if len(prerequisites) < self.MIN_PREREQUISITES:
            issues.append(
                f"Only {len(prerequisites)} prerequisites, need >= {self.MIN_PREREQUISITES}"
            )
        else:
            for i, prereq in enumerate(prerequisites):
                if isinstance(prereq, str):
                    self._check_placeholder_text(prereq, f"prerequisite {i + 1}", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.80 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for audience_fit."""
        return [
            "Define a specific primary audience with name and experience level",
            "Explain why the content is relevant for this audience (20+ chars)",
            f"List at least {self.MIN_PREREQUISITES} prerequisites needed to understand the content",
            "Be specific about experience levels (beginner/intermediate/advanced/expert)",
            "Avoid placeholder text in any field",
        ]


class ActionableValidator(AgentOutputValidator):
    """Validator for actionable agent outputs.

    Validation rules:
    - >= 1 immediate action (up to 3)
    - Each action has concrete next step (time_estimate, expected_outcome)
    - Quick win is present and actionable
    """

    agent_type: ClassVar[str] = "actionable"
    MIN_IMMEDIATE_ACTIONS = 1

    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate actionable output."""
        issues: list[str] = []

        immediate_actions = output.get("immediate_actions", [])
        quick_win = output.get("quick_win", "")

        # Check immediate actions count
        if len(immediate_actions) < self.MIN_IMMEDIATE_ACTIONS:
            issues.append(
                f"Only {len(immediate_actions)} immediate actions, "
                f"need >= {self.MIN_IMMEDIATE_ACTIONS}"
            )

        # Check each action for completeness
        for i, action in enumerate(immediate_actions):
            if not isinstance(action, dict):
                issues.append(f"Immediate action {i + 1} is not a valid object")
                continue

            action_text = action.get("action", "")
            time_estimate = action.get("time_estimate", "")
            expected_outcome = action.get("expected_outcome", "")

            if not action_text or len(action_text) < MIN_ACTION_TEXT_LENGTH:
                issues.append(f"Immediate action {i + 1} text is missing or too short")
            if not time_estimate:
                issues.append(f"Immediate action {i + 1} missing time_estimate")
            if not expected_outcome or len(expected_outcome) < MIN_OUTCOME_LENGTH:
                issues.append(f"Immediate action {i + 1} missing or short expected_outcome")

            self._check_placeholder_text(action_text, f"action {i + 1}", issues)
            self._check_generic_text(action_text, f"action {i + 1}", issues)

        # Check quick win
        if not quick_win or len(quick_win) < MIN_QUICK_WIN_LENGTH:
            issues.append(f"Quick win is missing or too short (< {MIN_QUICK_WIN_LENGTH} chars)")
        else:
            self._check_placeholder_text(quick_win, "quick_win", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for actionable."""
        return [
            f"Provide at least {self.MIN_IMMEDIATE_ACTIONS} immediate action(s) with specific steps",
            "Each action must have a time_estimate (e.g., '15 minutes', '1 hour')",
            "Each action must have a concrete expected_outcome (20+ chars)",
            "Include a quick_win that can be completed in 30 minutes or less",
            "Actions should start with a verb and be specific, not vague",
        ]


class TechComparatorValidator(AgentOutputValidator):
    """Validator for tech_comparator agent outputs.

    Validation rules:
    - Technologies mentioned by name (primary_tech required)
    - Comparison table/matrix provided with entries
    - Recommendation is substantive
    """

    agent_type: ClassVar[str] = "tech_comparator"
    MIN_ALTERNATIVES = 1

    def validate(self, output: dict[str, Any]) -> ValidationResult:
        """Validate tech_comparator output."""
        issues: list[str] = []

        primary_tech = output.get("primary_tech", "")
        alternatives = output.get("alternatives", [])
        comparison = output.get("comparison", {})
        recommendation = output.get("recommendation", "")

        # Check primary tech
        if not primary_tech or len(primary_tech) < MIN_TECH_NAME_LENGTH:
            issues.append("Primary technology name is missing or too short")

        # Check alternatives
        if len(alternatives) < self.MIN_ALTERNATIVES:
            issues.append(f"Only {len(alternatives)} alternatives, need >= {self.MIN_ALTERNATIVES}")

        # Check comparison table
        if not comparison or not isinstance(comparison, dict):
            issues.append("Comparison table is missing or empty")
        else:
            # Verify comparison has entries for primary_tech and alternatives
            expected_techs = {primary_tech.lower()} if primary_tech else set()
            expected_techs.update(alt.lower() for alt in alternatives if isinstance(alt, str))

            actual_techs = {k.lower() for k in comparison}
            missing_techs = expected_techs - actual_techs

            if missing_techs and len(missing_techs) > 1:
                issues.append(f"Comparison missing entries for: {', '.join(missing_techs)}")

            # Check each comparison entry has pros/cons
            for tech_name, entry in comparison.items():
                if not isinstance(entry, dict):
                    issues.append(f"Comparison entry for '{tech_name}' is invalid")
                    continue

                pros = entry.get("pros", [])
                cons = entry.get("cons", [])

                if not pros:
                    issues.append(f"'{tech_name}' comparison has no pros listed")
                if not cons:
                    issues.append(f"'{tech_name}' comparison has no cons listed")

        # Check recommendation
        if not recommendation or len(recommendation) < MIN_VERDICT_LENGTH:
            issues.append(f"Recommendation is missing or too short (< {MIN_VERDICT_LENGTH} chars)")
        else:
            self._check_placeholder_text(recommendation, "recommendation", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues)
            <= MAX_RETRYABLE_ISSUES + 1,  # Tech comparison can have more issues
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for tech_comparator."""
        return [
            "Identify the primary technology by name (not vague descriptions)",
            f"List at least {self.MIN_ALTERNATIVES} alternative technologies for comparison",
            "Provide a comparison entry for each technology with pros, cons, and use_cases",
            "Include specific pros and cons for each technology (not empty lists)",
            f"Write a substantive recommendation ({MIN_VERDICT_LENGTH}+ chars) explaining the choice",
        ]


class SecurityAuditorValidator(AgentOutputValidator):
    """Validator for security_auditor agent outputs.

    Validation rules:
    - Severity levels are valid enum values
    - No generic "review code" advice
    - Security risks have specific mitigations
    """

    agent_type: ClassVar[str] = "security_auditor"
    VALID_SEVERITIES: ClassVar[set[str]] = {"low", "medium", "high", "critical"}
    GENERIC_SECURITY_ADVICE: ClassVar[list[str]] = [
        "review code",
        "be careful",
        "check security",
        "follow best practices",
        "use secure methods",
    ]

    def validate(self, output: dict[str, Any]) -> ValidationResult:  # noqa: PLR0912
        """Validate security_auditor output."""
        issues: list[str] = []

        security_risks = output.get("security_risks", [])
        best_practices = output.get("best_practices", [])
        recommendation = output.get("recommendation", "")

        # Check security risks
        for i, risk in enumerate(security_risks):
            if not isinstance(risk, dict):
                issues.append(f"Security risk {i + 1} is not a valid object")
                continue

            severity = risk.get("severity", "")
            description = risk.get("description", "")
            mitigation = risk.get("mitigation", "")

            # Check severity is valid enum
            if severity.lower() not in self.VALID_SEVERITIES:
                issues.append(
                    f"Security risk {i + 1} has invalid severity '{severity}' "
                    f"(must be: {', '.join(self.VALID_SEVERITIES)})"
                )

            # Check for generic advice
            if description:
                desc_lower = description.lower()
                for generic in self.GENERIC_SECURITY_ADVICE:
                    if generic in desc_lower and len(description) < MIN_SECURITY_DESCRIPTION_LENGTH:
                        issues.append(
                            f"Security risk {i + 1} description is too generic: '{generic}'"
                        )
                        break

            if mitigation:
                mit_lower = mitigation.lower()
                for generic in self.GENERIC_SECURITY_ADVICE:
                    if generic in mit_lower and len(mitigation) < MIN_QUICK_WIN_LENGTH:
                        issues.append(
                            f"Security risk {i + 1} mitigation is too generic: '{generic}'"
                        )
                        break

            self._check_placeholder_text(description, f"risk {i + 1} description", issues)
            self._check_placeholder_text(mitigation, f"risk {i + 1} mitigation", issues)

        # Check best practices aren't all generic
        generic_count = 0
        for practice in best_practices:
            if isinstance(practice, str):
                practice_lower = practice.lower()
                for generic in self.GENERIC_SECURITY_ADVICE:
                    if generic in practice_lower:
                        generic_count += 1
                        break

        if best_practices and generic_count == len(best_practices):
            issues.append("All best practices are generic - provide specific recommendations")

        # Check recommendation
        if recommendation:
            self._check_placeholder_text(recommendation, "recommendation", issues)
            self._check_generic_text(recommendation, "recommendation", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for security_auditor."""
        return [
            f"Use valid severity levels: {', '.join(self.VALID_SEVERITIES)}",
            "Provide specific security risks with detailed descriptions (not 'review code')",
            "Each risk must have a concrete mitigation action",
            "Reference specific vulnerability types (OWASP, CVE) where applicable",
            "Best practices should be actionable, not generic advice",
        ]


class ImplementationPlannerValidator(AgentOutputValidator):
    """Validator for implementation_planner agent outputs.

    Validation rules:
    - Steps are ordered (step numbers sequential)
    - Prerequisites identified
    - Each step has an action
    - Estimated time is provided
    """

    agent_type: ClassVar[str] = "implementation_planner"
    MIN_STEPS = 2
    MIN_PREREQUISITES = 1

    def validate(self, output: dict[str, Any]) -> ValidationResult:  # noqa: PLR0912
        """Validate implementation_planner output."""
        issues: list[str] = []

        prerequisites = output.get("prerequisites", [])
        steps = output.get("steps", [])
        estimated_time = output.get("estimated_time", "")
        testing_strategy = output.get("testing_strategy", "")

        # Check prerequisites
        if len(prerequisites) < self.MIN_PREREQUISITES:
            issues.append(
                f"Only {len(prerequisites)} prerequisites, need >= {self.MIN_PREREQUISITES}"
            )

        for i, prereq in enumerate(prerequisites):
            if isinstance(prereq, str):
                self._check_placeholder_text(prereq, f"prerequisite {i + 1}", issues)

        # Check steps
        if len(steps) < self.MIN_STEPS:
            issues.append(f"Only {len(steps)} steps, need >= {self.MIN_STEPS}")

        # Check step ordering and content
        step_numbers = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                issues.append(f"Step {i + 1} is not a valid object")
                continue

            step_num = step.get("step")
            action = step.get("action", "")

            if step_num is not None:
                step_numbers.append(step_num)

            if not action or len(action) < MIN_AUDIENCE_NAME_LENGTH:
                issues.append(f"Step {i + 1} action is missing or too short")
            else:
                self._check_placeholder_text(action, f"step {i + 1} action", issues)

        # Check if step numbers are sequential
        if step_numbers:
            expected = list(range(1, len(step_numbers) + 1))
            if sorted(step_numbers) != expected:
                issues.append("Step numbers are not sequential (should be 1, 2, 3, ...)")

        # Check estimated time
        if not estimated_time:
            issues.append("Estimated time is missing")
        else:
            self._check_placeholder_text(estimated_time, "estimated_time", issues)

        # Check testing strategy
        if testing_strategy:
            self._check_placeholder_text(testing_strategy, "testing_strategy", issues)

        # Check confidence
        self._check_confidence_score(output, issues)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=0.85 if is_valid else 0.4,
            retry_recommended=len(issues) <= MAX_RETRYABLE_ISSUES,
        )

    def get_correction_hints(self) -> list[str]:
        """Get correction hints for implementation_planner."""
        return [
            f"List at least {self.MIN_PREREQUISITES} prerequisites for implementation",
            f"Provide at least {self.MIN_STEPS} sequential implementation steps",
            "Step numbers must be sequential (1, 2, 3, ...)",
            "Each step must have a concrete action starting with a verb",
            "Include an estimated_time for the full implementation (e.g., '2-3 hours')",
        ]


# =============================================================================
# Validator Registry
# =============================================================================

AGENT_VALIDATORS: dict[str, type[AgentOutputValidator]] = {
    "key_insights": KeyInsightsValidator,
    "pros_cons": ProsConsValidator,
    "audience_fit": AudienceFitValidator,
    "actionable": ActionableValidator,
    "tech_comparator": TechComparatorValidator,
    "security_auditor": SecurityAuditorValidator,
    "implementation_planner": ImplementationPlannerValidator,
}


def get_validator(agent_type: str) -> AgentOutputValidator | None:
    """Get validator for agent type, or None if no validation configured.

    Args:
        agent_type: Type of agent (e.g., 'key_insights', 'pros_cons')

    Returns:
        Validator instance or None if agent type has no validator

    """
    validator_class = AGENT_VALIDATORS.get(agent_type)
    if validator_class:
        return validator_class()
    return None


def validate_agent_output(
    output: dict[str, Any],
    agent_type: str,
) -> ValidationResult | None:
    """Validate agent output using the appropriate validator.

    Args:
        output: Agent findings dictionary
        agent_type: Type of agent

    Returns:
        ValidationResult or None if no validator exists for agent type

    """
    validator = get_validator(agent_type)
    if validator:
        result = validator.validate(output)
        if not result.is_valid:
            logger.warning(
                "agent_output_validation_failed",
                agent_type=agent_type,
                issues=result.issues,
                retry_recommended=result.retry_recommended,
            )
        return result
    return None
