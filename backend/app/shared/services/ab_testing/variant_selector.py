"""Variant selector for A/B testing with deterministic assignment.

This module provides deterministic hash-based assignment of analyses to
treatment/control groups for A/B testing of advanced LLM techniques.

Usage:
    from app.shared.services.ab_testing import get_variant_selector

    selector = get_variant_selector()
    variant = selector.select_variant("analysis-123", "few_shot_prompting")

    if variant == "treatment":
        # Use few-shot agent
        agent = create_few_shot_agent(...)
    else:
        # Use baseline agent
        agent = create_baseline_agent(...)

"""

from functools import lru_cache
from typing import Literal

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger

logger = get_logger(__name__)

VariantType = Literal["control", "treatment"]


class VariantSelector:
    """Deterministic variant selector for A/B testing.

    Uses hash-based assignment to ensure:
    - Same analysis_id always gets same variant
    - Configurable treatment percentage (default 20%)
    - Consistent across restarts (uses deterministic hashing)
    """

    def __init__(self):
        """Initialize VariantSelector with technique flags."""
        self.flags = get_technique_flags()

    def select_variant(
        self,
        analysis_id: str,
        technique: str,
    ) -> VariantType:
        """Select variant (control/treatment) for given analysis and technique.

        Uses deterministic hashing to ensure consistent assignment across calls.
        The same analysis_id will always be assigned to the same variant.

        Args:
            analysis_id: Unique identifier for the analysis (string or UUID).
            technique: Name of the technique being tested (e.g., "few_shot_prompting").

        Returns:
            "control" or "treatment" based on deterministic hash assignment.

        Example:
            >>> selector = VariantSelector()
            >>> selector.select_variant("analysis-123", "few_shot_prompting")
            "treatment"
            >>> selector.select_variant("analysis-123", "few_shot_prompting")
            "treatment"  # Same ID returns same variant

        """
        # If A/B testing is disabled, always return control
        if not self.flags.ab_test_enabled:
            return "control"

        # Deterministic assignment based on analysis_id hash
        # Combine analysis_id with technique name to allow different experiments
        # per technique (e.g., analysis-123 might be treatment for few-shot but
        # control for caching)
        hash_input = f"{analysis_id}:{technique}"
        hash_value = hash(hash_input) % 100

        # Assign to treatment group based on configured percentage
        treatment_threshold = int(self.flags.ab_test_treatment_pct * 100)
        variant: VariantType = "treatment" if hash_value < treatment_threshold else "control"

        logger.debug(
            "variant_selected",
            analysis_id=analysis_id,
            technique=technique,
            variant=variant,
            hash_value=hash_value,
            treatment_threshold=treatment_threshold,
        )

        return variant

    def is_treatment(self, analysis_id: str, technique: str) -> bool:
        """Check if analysis should receive treatment variant.

        Convenience method that returns True for treatment, False for control.

        Args:
            analysis_id: Unique identifier for the analysis.
            technique: Name of the technique being tested.

        Returns:
            True if treatment, False if control.

        """
        return self.select_variant(analysis_id, technique) == "treatment"


@lru_cache
def get_variant_selector() -> VariantSelector:
    """Get cached variant selector instance.

    Returns:
        VariantSelector: Cached instance for consistent variant selection.

    """
    return VariantSelector()
