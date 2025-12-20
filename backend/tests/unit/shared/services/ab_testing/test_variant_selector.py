"""Unit tests for variant selector.

Note: As of Dec 2025, all advanced techniques are enabled by default.
The VariantSelector now always returns "treatment" - these tests verify that behavior.
"""

import pytest

from app.shared.services.ab_testing.variant_selector import (
    VariantSelector,
    get_variant_selector,
)


@pytest.mark.unit
class TestVariantSelector:
    """Tests for simplified VariantSelector class."""

    def test_select_variant_always_returns_treatment(self):
        """VariantSelector always returns treatment (all features enabled)."""
        selector = VariantSelector()

        variant = selector.select_variant("analysis-123", "few_shot_prompting")

        assert variant == "treatment"

    def test_is_treatment_always_returns_true(self):
        """is_treatment always returns True (all features enabled)."""
        selector = VariantSelector()

        result = selector.is_treatment("analysis-123", "few_shot_prompting")

        assert result is True

    def test_works_with_any_analysis_id(self):
        """Selector works with any analysis ID format."""
        selector = VariantSelector()

        # UUID format
        assert (
            selector.select_variant("123e4567-e89b-12d3-a456-426614174000", "tech") == "treatment"
        )
        # Simple string
        assert selector.select_variant("analysis-123", "tech") == "treatment"
        # Empty string
        assert selector.select_variant("", "tech") == "treatment"

    def test_works_with_any_technique(self):
        """Selector works with any technique name."""
        selector = VariantSelector()

        assert selector.select_variant("id", "few_shot_prompting") == "treatment"
        assert selector.select_variant("id", "prompt_caching") == "treatment"
        assert selector.select_variant("id", "cot_supervisor") == "treatment"


@pytest.mark.unit
class TestGetVariantSelector:
    """Tests for get_variant_selector caching function."""

    def test_returns_variant_selector_instance(self):
        """get_variant_selector returns VariantSelector instance."""
        get_variant_selector.cache_clear()
        selector = get_variant_selector()

        assert isinstance(selector, VariantSelector)

    def test_caching_returns_same_instance(self):
        """get_variant_selector returns cached instance."""
        get_variant_selector.cache_clear()
        selector1 = get_variant_selector()
        selector2 = get_variant_selector()

        assert selector1 is selector2

    def test_cache_can_be_cleared(self):
        """Cache can be cleared to get new instance."""
        get_variant_selector.cache_clear()
        selector1 = get_variant_selector()

        get_variant_selector.cache_clear()
        selector2 = get_variant_selector()

        assert selector1 is not selector2
