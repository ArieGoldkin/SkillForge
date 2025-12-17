"""Variant selector for experiments with deterministic assignment.

This module provides deterministic hash-based assignment of analyses to
treatment/control groups for evaluating LLM technique effectiveness.

Note: As of Dec 2025, all advanced techniques are enabled by default.
This selector now always returns "treatment" - all analyses use enhanced features.
The A/B testing infrastructure is preserved for future experiments.

Usage:
    from app.shared.services.ab_testing import get_variant_selector

    selector = get_variant_selector()
    variant = selector.select_variant("analysis-123", "few_shot_prompting")
    # Always returns "treatment" - features are always on

"""

from functools import lru_cache
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)

VariantType = Literal["control", "treatment"]


class VariantSelector:
    """Deterministic variant selector for experiments.

    As of Dec 2025, all techniques are enabled by default.
    This class always returns "treatment" for all analyses.

    The infrastructure is preserved for future experiments where
    we may want to compare different technique variations.
    """

    def select_variant(
        self,
        analysis_id: str,
        technique: str,
    ) -> VariantType:
        """Select variant for given analysis and technique.

        Always returns "treatment" as all features are now enabled by default.

        Args:
            analysis_id: Unique identifier for the analysis.
            technique: Name of the technique (for logging/future use).

        Returns:
            Always "treatment" - all features are enabled.

        """
        logger.debug(
            "variant_selected",
            analysis_id=analysis_id,
            technique=technique,
            variant="treatment",
            note="all_features_enabled_by_default",
        )
        return "treatment"

    def is_treatment(self, analysis_id: str, technique: str) -> bool:
        """Check if analysis should receive treatment variant.

        Always returns True as all features are enabled.

        Args:
            analysis_id: Unique identifier for the analysis.
            technique: Name of the technique.

        Returns:
            Always True - all features are enabled.

        """
        return True


@lru_cache
def get_variant_selector() -> VariantSelector:
    """Get cached variant selector instance.

    Returns:
        VariantSelector: Cached instance for consistent variant selection.

    """
    return VariantSelector()
