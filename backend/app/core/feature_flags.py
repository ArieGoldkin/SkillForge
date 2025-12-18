"""Configuration for LLM techniques and prompt engineering.

This module provides configuration values (not on/off flags) for LLM techniques.
All techniques are ALWAYS enabled - these settings control their behavior.

Philosophy: No more "enable_X = False" flags that never get turned on.
Instead, configure the parameters and always use the feature.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PromptTechniqueConfig(BaseSettings):
    """Configuration for prompt engineering techniques.

    These are configuration values, not feature flags.
    All techniques are always enabled - configure how they behave.
    """

    # Few-Shot Prompting Configuration
    few_shot_max_examples: int = 3
    few_shot_min_quality: float = 0.8
    few_shot_use_semantic: bool = True

    # Chain-of-Thought Configuration
    cot_content_threshold: int = 5000
    cot_reasoning_model: str = "claude-sonnet-4-20250514"

    # Tree-of-Thought Configuration
    tot_conflict_threshold: float = 0.3

    # ReAct Tracing Configuration
    react_max_iterations: int = 5

    model_config = SettingsConfigDict(
        env_prefix="TECHNIQUE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_technique_config() -> PromptTechniqueConfig:
    """Get cached technique configuration.

    Returns:
        PromptTechniqueConfig: Cached instance loaded from environment.

    """
    return PromptTechniqueConfig()
