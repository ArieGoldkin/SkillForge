"""Feature flags for advanced LLM techniques.

All techniques are disabled by default and enabled via environment variables.
This allows gradual rollout and instant rollback.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TechniqueFlags(BaseSettings):
    """Feature flags for LLM techniques."""

    # Phase 1: Few-Shot Prompting
    enable_few_shot: bool = False
    few_shot_max_examples: int = 3
    few_shot_min_quality: float = 0.8
    few_shot_use_semantic: bool = True

    # Phase 2: CoT Supervisor
    enable_cot_supervisor: bool = False
    cot_content_threshold: int = 5000
    cot_reasoning_model: str = "claude-sonnet-4-20250514"

    # Phase 3: Caching
    enable_redis_cache: bool = False
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 86400
    redis_similarity_threshold: float = 0.92
    enable_prompt_caching: bool = False
    prompt_cache_ttl: int = 300

    # Phase 4: ToT
    enable_tot_resolver: bool = False
    tot_conflict_threshold: float = 0.3

    # Phase 5: ReAct
    enable_react_tracing: bool = False
    react_max_iterations: int = 5

    # A/B Testing
    ab_test_enabled: bool = False
    ab_test_treatment_pct: float = 0.2  # 20% traffic

    model_config = SettingsConfigDict(
        env_prefix="TECHNIQUE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_technique_flags() -> TechniqueFlags:
    """Get cached technique flags.

    Returns:
        TechniqueFlags: Cached instance of technique flags loaded from environment.

    """
    return TechniqueFlags()


def is_treatment_group(analysis_id: str) -> bool:
    """Determine if analysis should use experimental features (A/B test).

    Uses deterministic hashing to assign analyses to treatment/control groups.
    The same analysis_id will always be assigned to the same group.

    Args:
        analysis_id: Unique identifier for the analysis (string or UUID).

    Returns:
        bool: True if analysis should receive experimental features, False otherwise.

    """
    flags = get_technique_flags()
    if not flags.ab_test_enabled:
        return False

    # Deterministic assignment based on analysis_id hash
    hash_value = hash(analysis_id) % 100
    return hash_value < (flags.ab_test_treatment_pct * 100)
