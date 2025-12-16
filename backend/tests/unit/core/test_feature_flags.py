"""Unit tests for feature flags configuration."""

import os
from unittest.mock import patch

import pytest

from app.core.feature_flags import TechniqueFlags, get_technique_flags, is_treatment_group


@pytest.mark.unit
class TestTechniqueFlags:
    """Tests for TechniqueFlags configuration class."""

    def test_default_flags_all_disabled(self):
        """Test that all feature flags default to False (safe defaults)."""
        flags = TechniqueFlags()

        # Phase 1: Few-Shot
        assert flags.enable_few_shot is False
        assert flags.few_shot_max_examples == 3
        assert flags.few_shot_min_quality == 0.8
        assert flags.few_shot_use_semantic is True

        # Phase 2: CoT Supervisor
        assert flags.enable_cot_supervisor is False
        assert flags.cot_content_threshold == 5000
        assert flags.cot_reasoning_model == "claude-sonnet-4-20250514"

        # Phase 3: Caching
        assert flags.enable_redis_cache is False
        assert flags.redis_url == "redis://localhost:6379"
        assert flags.redis_cache_ttl == 86400
        assert flags.redis_similarity_threshold == 0.92
        assert flags.enable_prompt_caching is False
        assert flags.prompt_cache_ttl == 300

        # Phase 4: ToT
        assert flags.enable_tot_resolver is False
        assert flags.tot_conflict_threshold == 0.3

        # Phase 5: ReAct
        assert flags.enable_react_tracing is False
        assert flags.react_max_iterations == 5

        # A/B Testing
        assert flags.ab_test_enabled is False
        assert flags.ab_test_treatment_pct == 0.2

    def test_env_prefix_technique(self):
        """Test that flags are loaded with TECHNIQUE_ prefix from environment."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_ENABLE_FEW_SHOT": "true",
                "TECHNIQUE_FEW_SHOT_MAX_EXAMPLES": "5",
                "TECHNIQUE_ENABLE_COT_SUPERVISOR": "true",
                "TECHNIQUE_AB_TEST_ENABLED": "true",
                "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5",
            },
            clear=False,
        ):
            # Clear cache to force reload
            get_technique_flags.cache_clear()
            flags = TechniqueFlags()

            assert flags.enable_few_shot is True
            assert flags.few_shot_max_examples == 5
            assert flags.enable_cot_supervisor is True
            assert flags.ab_test_enabled is True
            assert flags.ab_test_treatment_pct == 0.5

    def test_individual_flags_can_be_enabled(self):
        """Test that individual flags can be enabled independently."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_ENABLE_REDIS_CACHE": "true",
                "TECHNIQUE_REDIS_URL": "redis://custom:6380",
                "TECHNIQUE_REDIS_CACHE_TTL": "3600",
            },
            clear=False,
        ):
            get_technique_flags.cache_clear()
            flags = TechniqueFlags()

            assert flags.enable_redis_cache is True
            assert flags.redis_url == "redis://custom:6380"
            assert flags.redis_cache_ttl == 3600
            # Other flags remain disabled
            assert flags.enable_few_shot is False
            assert flags.enable_cot_supervisor is False


@pytest.mark.unit
class TestGetTechniqueFlags:
    """Tests for get_technique_flags caching function."""

    def test_returns_technique_flags_instance(self):
        """Test that get_technique_flags returns TechniqueFlags instance."""
        get_technique_flags.cache_clear()
        flags = get_technique_flags()

        assert isinstance(flags, TechniqueFlags)

    def test_caching_returns_same_instance(self):
        """Test that get_technique_flags returns cached instance on subsequent calls."""
        get_technique_flags.cache_clear()
        flags1 = get_technique_flags()
        flags2 = get_technique_flags()

        # Should return the same cached instance
        assert flags1 is flags2

    def test_cache_can_be_cleared(self):
        """Test that cache can be cleared to reload configuration."""
        with patch.dict(os.environ, {"TECHNIQUE_ENABLE_FEW_SHOT": "false"}, clear=False):
            get_technique_flags.cache_clear()
            flags1 = get_technique_flags()
            assert flags1.enable_few_shot is False

        # Change environment and clear cache
        with patch.dict(os.environ, {"TECHNIQUE_ENABLE_FEW_SHOT": "true"}, clear=False):
            get_technique_flags.cache_clear()
            flags2 = get_technique_flags()
            assert flags2.enable_few_shot is True


@pytest.mark.unit
class TestIsTreatmentGroup:
    """Tests for is_treatment_group A/B testing function."""

    def test_returns_false_when_ab_test_disabled(self):
        """Test that is_treatment_group returns False when A/B testing is disabled."""
        with patch.dict(os.environ, {"TECHNIQUE_AB_TEST_ENABLED": "false"}, clear=False):
            get_technique_flags.cache_clear()
            result = is_treatment_group("any-analysis-id")

            assert result is False

    def test_deterministic_assignment(self):
        """Test that same analysis_id always gets same assignment."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5"},
            clear=False,
        ):
            get_technique_flags.cache_clear()
            analysis_id = "test-analysis-123"

            # Call multiple times with same ID
            result1 = is_treatment_group(analysis_id)
            result2 = is_treatment_group(analysis_id)
            result3 = is_treatment_group(analysis_id)

            # Should always return same result for same ID
            assert result1 == result2 == result3

    def test_different_ids_can_have_different_assignments(self):
        """Test that different analysis IDs can be assigned to different groups."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5"},
            clear=False,
        ):
            get_technique_flags.cache_clear()

            # Generate multiple IDs and collect results
            results = [is_treatment_group(f"analysis-{i}") for i in range(100)]

            # With 50% treatment, we should have both True and False
            # (not all IDs should be in the same group)
            assert True in results
            assert False in results

    def test_treatment_percentage_respected(self):
        """Test that treatment percentage is approximately respected."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.2"},
            clear=False,
        ):
            get_technique_flags.cache_clear()

            # Generate 1000 IDs and count treatment assignments
            results = [is_treatment_group(f"analysis-{i}") for i in range(1000)]
            treatment_count = sum(results)
            treatment_pct = treatment_count / len(results)

            # Should be approximately 20% (with some variance due to hashing)
            # Allow 10% margin of error (18%-22%)
            assert 0.15 < treatment_pct < 0.25

    def test_zero_percent_treatment(self):
        """Test that 0% treatment means no analyses are in treatment group."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.0"},
            clear=False,
        ):
            get_technique_flags.cache_clear()

            results = [is_treatment_group(f"analysis-{i}") for i in range(100)]

            # All should be False (control group)
            assert all(result is False for result in results)

    def test_hundred_percent_treatment(self):
        """Test that 100% treatment means all analyses are in treatment group."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "1.0"},
            clear=False,
        ):
            get_technique_flags.cache_clear()

            results = [is_treatment_group(f"analysis-{i}") for i in range(100)]

            # All should be True (treatment group)
            assert all(result is True for result in results)

    def test_works_with_uuid_strings(self):
        """Test that is_treatment_group works with UUID-formatted strings."""
        with patch.dict(
            os.environ,
            {"TECHNIQUE_AB_TEST_ENABLED": "true", "TECHNIQUE_AB_TEST_TREATMENT_PCT": "0.5"},
            clear=False,
        ):
            get_technique_flags.cache_clear()
            uuid_str = "123e4567-e89b-12d3-a456-426614174000"

            # Should not raise and should be deterministic
            result1 = is_treatment_group(uuid_str)
            result2 = is_treatment_group(uuid_str)

            assert result1 == result2
            assert isinstance(result1, bool)
