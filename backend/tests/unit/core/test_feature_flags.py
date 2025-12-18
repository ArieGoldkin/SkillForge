"""Unit tests for prompt technique configuration."""

import os
from unittest.mock import patch

import pytest

from app.core.feature_flags import (
    PromptTechniqueConfig,
    get_technique_config,
)


@pytest.mark.unit
class TestPromptTechniqueConfig:
    """Tests for PromptTechniqueConfig configuration class."""

    def test_default_config_values(self):
        """Test that configuration has sensible defaults."""
        config = PromptTechniqueConfig()

        # Few-Shot Configuration
        assert config.few_shot_max_examples == 3
        assert config.few_shot_min_quality == 0.8
        assert config.few_shot_use_semantic is True

        # Chain-of-Thought Configuration
        assert config.cot_content_threshold == 5000
        assert config.cot_reasoning_model == "claude-sonnet-4-20250514"

        # Tree-of-Thought Configuration
        assert config.tot_conflict_threshold == 0.3

        # ReAct Configuration
        assert config.react_max_iterations == 5

    def test_env_prefix_technique(self):
        """Test that config loads with TECHNIQUE_ prefix from environment."""
        with patch.dict(
            os.environ,
            {
                "TECHNIQUE_FEW_SHOT_MAX_EXAMPLES": "5",
                "TECHNIQUE_COT_CONTENT_THRESHOLD": "10000",
            },
            clear=False,
        ):
            # Clear cache to force reload
            get_technique_config.cache_clear()
            config = PromptTechniqueConfig()

            assert config.few_shot_max_examples == 5
            assert config.cot_content_threshold == 10000


@pytest.mark.unit
class TestGetTechniqueConfig:
    """Tests for get_technique_config caching function."""

    def test_returns_config_instance(self):
        """Test that get_technique_config returns PromptTechniqueConfig instance."""
        get_technique_config.cache_clear()
        config = get_technique_config()

        assert isinstance(config, PromptTechniqueConfig)

    def test_caching_returns_same_instance(self):
        """Test that get_technique_config returns cached instance."""
        get_technique_config.cache_clear()
        config1 = get_technique_config()
        config2 = get_technique_config()

        assert config1 is config2

    def test_cache_can_be_cleared(self):
        """Test that cache can be cleared to reload configuration."""
        get_technique_config.cache_clear()
        config1 = get_technique_config()

        get_technique_config.cache_clear()
        config2 = get_technique_config()

        # After cache clear, should get different instance
        assert config1 is not config2
