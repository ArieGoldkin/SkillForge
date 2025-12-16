"""Unit tests for variant selector (A/B testing)."""

import os
from unittest.mock import patch

import pytest

from app.shared.services.ab_testing.variant_selector import (
    VariantSelector,
    get_variant_selector,
)


@pytest.mark.unit
class TestVariantSelector:
    """Tests for VariantSelector class."""

    def test_initialization(self):
        """VariantSelector initializes with technique flags."""
        selector = VariantSelector()
        assert selector.flags is not None

    def test_returns_control_when_ab_test_disabled(self):
        """select_variant() returns control when A/B testing is disabled."""
        with patch.dict(os.environ, {"TECHNIQUE_AB_TEST_ENABLED": "false"}, clear=False):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            variant = selector.select_variant("analysis-123", "few_shot_prompting")
            assert variant == "control"

    def test_deterministic_assignment_same_id(self):
        """Same analysis_id always gets same variant (deterministic)."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            analysis_id = "analysis-deterministic-123"
            technique = "few_shot_prompting"

            # Call multiple times with same ID
            variant1 = selector.select_variant(analysis_id, technique)
            variant2 = selector.select_variant(analysis_id, technique)
            variant3 = selector.select_variant(analysis_id, technique)

            # Should always return same variant
            assert variant1 == variant2 == variant3

    def test_different_ids_can_have_different_variants(self):
        """Different analysis IDs can be assigned to different variants."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # Generate multiple IDs and collect variants
            variants = [
                selector.select_variant(f"analysis-{i}", "few_shot_prompting")
                for i in range(100)
            ]

            # With 50% treatment, we should have both variants
            assert "control" in variants
            assert "treatment" in variants

    def test_treatment_percentage_respected(self):
        """Treatment percentage is approximately respected over many samples."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.2",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # Generate 1000 IDs and count treatment assignments
            variants = [
                selector.select_variant(f"analysis-{i}", "few_shot_prompting")
                for i in range(1000)
            ]
            treatment_count = sum(1 for v in variants if v == "treatment")
            treatment_pct = treatment_count / len(variants)

            # Should be approximately 20% (with some variance due to hashing)
            # Allow 5% margin of error (15%-25%)
            assert 0.15 < treatment_pct < 0.25

    def test_zero_percent_treatment(self):
        """0% treatment means all analyses are control."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.0",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            variants = [
                selector.select_variant(f"analysis-{i}", "few_shot_prompting")
                for i in range(100)
            ]

            # All should be control
            assert all(v == "control" for v in variants)

    def test_hundred_percent_treatment(self):
        """100% treatment means all analyses are treatment."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "1.0",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            variants = [
                selector.select_variant(f"analysis-{i}", "few_shot_prompting")
                for i in range(100)
            ]

            # All should be treatment
            assert all(v == "treatment" for v in variants)

    def test_works_with_uuid_strings(self):
        """select_variant() works with UUID-formatted strings."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            uuid_str = "123e4567-e89b-12d3-a456-426614174000"
            variant1 = selector.select_variant(uuid_str, "few_shot_prompting")
            variant2 = selector.select_variant(uuid_str, "few_shot_prompting")

            # Should be deterministic
            assert variant1 == variant2
            assert variant1 in ("control", "treatment")

    def test_technique_name_affects_assignment(self):
        """Different techniques can have different assignments for same ID."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            analysis_id = "analysis-multi-technique"

            # Same ID, different techniques can have different variants
            variant_few_shot = selector.select_variant(analysis_id, "few_shot_prompting")
            variant_caching = selector.select_variant(analysis_id, "prompt_caching")
            variant_cot = selector.select_variant(analysis_id, "cot_supervisor")

            # Each technique should be deterministic
            assert variant_few_shot == selector.select_variant(analysis_id, "few_shot_prompting")
            assert variant_caching == selector.select_variant(analysis_id, "prompt_caching")
            assert variant_cot == selector.select_variant(analysis_id, "cot_supervisor")

            # Different techniques CAN have different assignments (not guaranteed, but possible)
            # Just verify they're all valid variants
            assert variant_few_shot in ("control", "treatment")
            assert variant_caching in ("control", "treatment")
            assert variant_cot in ("control", "treatment")

    def test_is_treatment_convenience_method(self):
        """is_treatment() returns True for treatment, False for control."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "1.0",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # 100% treatment should always return True
            assert selector.is_treatment("analysis-123", "few_shot_prompting") is True

        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.0",
            },
            clear=False,
        ):
            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # 0% treatment should always return False
            assert selector.is_treatment("analysis-456", "few_shot_prompting") is False


@pytest.mark.unit
class TestGetVariantSelector:
    """Tests for get_variant_selector caching function."""

    def test_returns_variant_selector_instance(self):
        """get_variant_selector() returns VariantSelector instance."""
        get_variant_selector.cache_clear()
        selector = get_variant_selector()
        assert isinstance(selector, VariantSelector)

    def test_caching_returns_same_instance(self):
        """get_variant_selector() returns cached instance on subsequent calls."""
        get_variant_selector.cache_clear()
        selector1 = get_variant_selector()
        selector2 = get_variant_selector()

        # Should return the same cached instance
        assert selector1 is selector2

    def test_cache_can_be_cleared(self):
        """Cache can be cleared to get new instance."""
        get_variant_selector.cache_clear()
        selector1 = get_variant_selector()

        get_variant_selector.cache_clear()
        selector2 = get_variant_selector()

        # After cache clear, should get different instance
        assert selector1 is not selector2


@pytest.mark.unit
class TestVariantSelectorEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_analysis_id(self):
        """Empty analysis_id is handled gracefully (uses empty string hash)."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # Empty ID should work (deterministic)
            variant1 = selector.select_variant("", "few_shot_prompting")
            variant2 = selector.select_variant("", "few_shot_prompting")

            assert variant1 == variant2
            assert variant1 in ("control", "treatment")

    def test_special_characters_in_analysis_id(self):
        """Analysis ID with special characters is handled correctly."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            special_ids = [
                "analysis-with-dash",
                "analysis_with_underscore",
                "analysis.with.dots",
                "analysis:with:colons",
                "analysis/with/slashes",
            ]

            for special_id in special_ids:
                variant = selector.select_variant(special_id, "few_shot_prompting")
                assert variant in ("control", "treatment")

    def test_very_long_analysis_id(self):
        """Very long analysis ID is handled without performance issues."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            from app.core.feature_flags import get_technique_flags

            get_technique_flags.cache_clear()
            selector = VariantSelector()

            # 1000 character ID
            long_id = "a" * 1000
            variant = selector.select_variant(long_id, "few_shot_prompting")
            assert variant in ("control", "treatment")
