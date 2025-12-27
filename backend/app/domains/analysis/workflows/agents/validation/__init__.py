"""Validation utilities for agent outputs.

This module provides three validation systems:

1. **Specificity Scoring** (existing): Measures vague language vs numeric specificity
2. **Output Validation** (Issue #507): Per-agent semantic validation with self-correction
3. **Execution Helpers** (Issue #507 Refactoring): Extracted validation helpers

Usage:
    # Specificity scoring (existing)
    from app.domains.analysis.workflows.agents.validation import score_agent_output

    # Output validation with self-correction (Issue #507)
    from app.domains.analysis.workflows.agents.validation import (
        get_validator,
        validate_agent_output,
        build_correction_prompt,
    )

    # Execution helpers (Issue #507 Refactoring)
    from app.domains.analysis.workflows.agents.validation import (
        run_self_correction_loop,
        validate_findings_count,
        validate_specificity_score,
    )
"""

from app.domains.analysis.workflows.agents.validation.correction_prompts import (
    build_correction_context,
    build_correction_prompt,
    get_agent_specific_guidance,
)
from app.domains.analysis.workflows.agents.validation.execution_helpers import (
    ValidationCheckResult,
    validate_findings_count,
    validate_specificity_score,
)
from app.domains.analysis.workflows.agents.validation.output_validators import (
    AGENT_VALIDATORS,
    ActionableValidator,
    AgentOutputValidator,
    AudienceFitValidator,
    ImplementationPlannerValidator,
    KeyInsightsValidator,
    ProsConsValidator,
    SecurityAuditorValidator,
    TechComparatorValidator,
    ValidationResult,
    get_validator,
    validate_agent_output,
)
from app.domains.analysis.workflows.agents.validation.self_correction import (
    SelfCorrectionResult,
    record_self_correction_metadata,
    run_self_correction_loop,
)
from app.domains.analysis.workflows.agents.validation.specificity_scorer import (
    NumericValue,
    SpecificityScore,
    SpecificityScorer,
    VaguePhrase,
    score_agent_output,
    validate_specificity_threshold,
)

__all__ = [
    # Output validation (Issue #507)
    "AGENT_VALIDATORS",
    "ActionableValidator",
    "AgentOutputValidator",
    "AudienceFitValidator",
    "ImplementationPlannerValidator",
    "KeyInsightsValidator",
    # Specificity scoring (existing)
    "NumericValue",
    "ProsConsValidator",
    "SecurityAuditorValidator",
    "SelfCorrectionResult",
    "SpecificityScore",
    "SpecificityScorer",
    "TechComparatorValidator",
    "VaguePhrase",
    "ValidationCheckResult",
    "ValidationResult",
    "build_correction_context",
    "build_correction_prompt",
    "get_agent_specific_guidance",
    "get_validator",
    "record_self_correction_metadata",
    "run_self_correction_loop",
    "score_agent_output",
    "validate_agent_output",
    "validate_findings_count",
    "validate_specificity_score",
    "validate_specificity_threshold",
]
