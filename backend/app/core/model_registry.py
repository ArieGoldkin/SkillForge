"""Model registry with December 2025 LLM pricing and capabilities.

This module provides a centralized registry of all supported LLM models
with their pricing, capabilities, and metadata for evaluation-driven
model selection.

Sources:
- IntuitionLabs LLM API Pricing Comparison 2025
- Official provider documentation (OpenAI, Anthropic, Google, xAI)
"""

from dataclasses import dataclass
from typing import Final, Literal

LatencyTier = Literal["fast", "medium", "slow"]
Provider = Literal["openai", "anthropic", "google_genai", "xai", "deepseek"]


@dataclass(frozen=True)
class ModelInfo:
    """Immutable model metadata for registry."""

    provider: Provider
    model_id: str
    display_name: str
    input_cost_per_1m: float  # USD per 1M input tokens
    output_cost_per_1m: float  # USD per 1M output tokens
    context_window: int  # Max context in tokens
    latency_tier: LatencyTier
    capabilities: tuple[str, ...]  # Frozen for hashability
    api_key_field: str
    notes: str = ""

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a given token count."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m
        return input_cost + output_cost


# =============================================================================
# DECEMBER 2025 MODEL REGISTRY
# =============================================================================
# Pricing sourced from IntuitionLabs (Dec 8, 2025) and official docs
# =============================================================================

MODEL_REGISTRY: Final[dict[str, ModelInfo]] = {
    # =========================================================================
    # OPENAI MODELS (December 2025)
    # =========================================================================
    "gpt-5": ModelInfo(
        provider="openai",
        model_id="gpt-5",
        display_name="GPT-5",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        context_window=128_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "agents", "multimodal"),
        api_key_field="OPENAI_API_KEY",
        notes="Flagship model, best for complex agents",
    ),
    "gpt-5-mini": ModelInfo(
        provider="openai",
        model_id="gpt-5-mini",
        display_name="GPT-5 Mini",
        input_cost_per_1m=0.25,
        output_cost_per_1m=2.00,
        context_window=128_000,
        latency_tier="fast",
        capabilities=("balanced", "coding", "general"),
        api_key_field="OPENAI_API_KEY",
        notes="Good balance of speed/quality/cost",
    ),
    "gpt-5-nano": ModelInfo(
        provider="openai",
        model_id="gpt-5-nano",
        display_name="GPT-5 Nano",
        input_cost_per_1m=0.05,
        output_cost_per_1m=0.40,
        context_window=64_000,
        latency_tier="fast",
        capabilities=("simple", "classification", "extraction"),
        api_key_field="OPENAI_API_KEY",
        notes="Cheapest OpenAI, good for simple tasks",
    ),
    "gpt-4o": ModelInfo(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_cost_per_1m=5.00,
        output_cost_per_1m=20.00,
        context_window=128_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "multimodal", "vision"),
        api_key_field="OPENAI_API_KEY",
        notes="Multimodal with vision support",
    ),
    "gpt-4o-mini": ModelInfo(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        input_cost_per_1m=0.60,
        output_cost_per_1m=2.40,
        context_window=128_000,
        latency_tier="fast",
        capabilities=("balanced", "coding", "multimodal"),
        api_key_field="OPENAI_API_KEY",
        notes="Current default, reliable and cost-effective",
    ),
    "o3-mini": ModelInfo(
        provider="openai",
        model_id="o3-mini",
        display_name="o3-mini",
        input_cost_per_1m=1.10,
        output_cost_per_1m=4.40,
        context_window=200_000,
        latency_tier="slow",
        capabilities=("reasoning", "math", "coding", "planning"),
        api_key_field="OPENAI_API_KEY",
        notes="Reasoning specialist, slower but more thorough",
    ),
    # =========================================================================
    # ANTHROPIC MODELS (December 2025)
    # =========================================================================
    "claude-opus-4-5-20251101": ModelInfo(
        provider="anthropic",
        model_id="claude-opus-4-5-20251101",
        display_name="Claude Opus 4.5",
        input_cost_per_1m=15.00,
        output_cost_per_1m=75.00,
        context_window=200_000,
        latency_tier="slow",
        capabilities=("top_reasoning", "coding", "agents", "architecture"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="Best reasoning, 48-76% fewer tokens than GPT-4",
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=200_000,
        latency_tier="medium",
        capabilities=("coding", "agents", "reasoning", "synthesis"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="SWE-bench leader (72.5%), best for coding/agents",
    ),
    "claude-haiku-3-5-20241022": ModelInfo(
        provider="anthropic",
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude Haiku 3.5",
        input_cost_per_1m=0.80,
        output_cost_per_1m=4.00,
        context_window=200_000,
        latency_tier="fast",
        capabilities=("fast", "balanced", "coding"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="Fast throughput, good for high-volume tasks",
    ),
    # =========================================================================
    # GOOGLE MODELS (December 2025)
    # =========================================================================
    "gemini-2.5-pro": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.5-pro",  # Use stable name, LangChain resolves to latest
        display_name="Gemini 2.5 Pro",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        context_window=1_000_000,
        latency_tier="medium",
        capabilities=("reasoning", "multimodal", "long_context"),
        api_key_field="GOOGLE_API_KEY",
        notes="1M context window, good for long docs",
    ),
    "gemini-2.5-flash": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.5-flash",  # Use stable name, LangChain resolves to latest
        display_name="Gemini 2.5 Flash",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("fast", "multimodal", "balanced"),
        api_key_field="GOOGLE_API_KEY",
        notes="Extremely cost-effective, 1M context",
    ),
    "gemini-2.0-flash": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("fast", "multimodal", "simple"),
        api_key_field="GOOGLE_API_KEY",
        notes="Previous gen, slightly cheaper",
    ),
    # =========================================================================
    # XAI MODELS (December 2025)
    # =========================================================================
    "grok-3": ModelInfo(
        provider="xai",
        model_id="grok-3",
        display_name="Grok 3",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=131_072,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "real_time"),
        api_key_field="XAI_API_KEY",
        notes="Strong reasoning, competitive with Claude Sonnet",
    ),
    "grok-3-fast": ModelInfo(
        provider="xai",
        model_id="grok-3-fast",
        display_name="Grok 3 Fast",
        input_cost_per_1m=5.00,
        output_cost_per_1m=25.00,
        context_window=131_072,
        latency_tier="fast",
        capabilities=("reasoning", "low_latency"),
        api_key_field="XAI_API_KEY",
        notes="Optimized for low latency",
    ),
    "grok-3-mini": ModelInfo(
        provider="xai",
        model_id="grok-3-mini",
        display_name="Grok 3 Mini",
        input_cost_per_1m=0.30,
        output_cost_per_1m=0.50,
        context_window=131_072,
        latency_tier="fast",
        capabilities=("balanced", "cost_effective"),
        api_key_field="XAI_API_KEY",
        notes="Good fallback option, very affordable",
    ),
    # =========================================================================
    # DEEPSEEK MODELS (December 2025)
    # =========================================================================
    "deepseek-v3": ModelInfo(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek V3.2",
        input_cost_per_1m=0.28,
        output_cost_per_1m=0.42,
        context_window=128_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "cost_effective"),
        api_key_field="DEEPSEEK_API_KEY",
        notes="90% cheaper than Western models, quality TBD for your tasks",
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_model_info(model_name: str) -> ModelInfo | None:
    """Get model info by name."""
    return MODEL_REGISTRY.get(model_name)


def list_models_by_provider(provider: Provider) -> list[str]:
    """List all models for a given provider."""
    return [name for name, info in MODEL_REGISTRY.items() if info.provider == provider]


def list_models_by_capability(capability: str) -> list[str]:
    """List all models that have a specific capability."""
    return [
        name for name, info in MODEL_REGISTRY.items() if capability in info.capabilities
    ]


def list_models_by_latency(tier: LatencyTier) -> list[str]:
    """List all models in a latency tier."""
    return [name for name, info in MODEL_REGISTRY.items() if info.latency_tier == tier]


def get_cheapest_models(top_n: int = 5) -> list[tuple[str, float]]:
    """Get the N cheapest models by estimated cost (1K input + 1K output)."""
    costs = []
    for name, info in MODEL_REGISTRY.items():
        # Estimate cost for typical request (1K in, 1K out)
        cost = info.estimate_cost(1000, 1000)
        costs.append((name, cost))
    return sorted(costs, key=lambda x: x[1])[:top_n]


def get_available_models(settings: object) -> list[str]:
    """Get models that have API keys configured.

    Args:
        settings: Settings object with API key attributes

    Returns:
        List of model names that can be used
    """
    available = []
    for name, info in MODEL_REGISTRY.items():
        api_key = getattr(settings, info.api_key_field, None)
        if api_key:
            available.append(name)
    return available


# =============================================================================
# TASK-BASED MODEL RECOMMENDATIONS (Initial Hypotheses - To Be Validated)
# =============================================================================
# These are HYPOTHESES to be validated by the evaluation framework.
# Do NOT assume these are correct - run experiments to find the real winners.
# =============================================================================

TASK_MODEL_HYPOTHESES: Final[dict[str, list[str]]] = {
    # Supervisor: needs fast classification, not complex reasoning
    "supervisor": [
        "gemini-2.5-flash",  # Hypothesis: fastest, cheapest
        "gpt-5-mini",  # Hypothesis: reliable fallback
        "grok-3-mini",  # Hypothesis: alternative
        "claude-haiku-3-5-20241022",  # Hypothesis: fast quality
    ],
    # Agent analysis: needs good reasoning and domain understanding
    "agent_analysis": [
        "gpt-5-mini",  # Hypothesis: balanced
        "claude-sonnet-4-20250514",  # Hypothesis: quality
        "gemini-2.5-flash",  # Hypothesis: cost-effective
        "grok-3-mini",  # Hypothesis: alternative
    ],
    # Synthesis: needs excellent summarization and coherence
    "synthesis": [
        "claude-sonnet-4-20250514",  # Hypothesis: best synthesis
        "gpt-5",  # Hypothesis: premium quality
        "gemini-2.5-pro",  # Hypothesis: long context
        "grok-3",  # Hypothesis: alternative
    ],
    # Tutoring: needs good explanation and teaching ability
    "tutoring": [
        "claude-sonnet-4-20250514",  # Hypothesis: best for teaching
        "gpt-5",  # Hypothesis: versatile
        "grok-3",  # Hypothesis: conversational
        "gemini-2.5-pro",  # Hypothesis: comprehensive
    ],
    # Code analysis: needs deep code understanding
    "code_analysis": [
        "claude-sonnet-4-20250514",  # Hypothesis: SWE-bench leader
        "gpt-5",  # Hypothesis: strong at code
        "o3-mini",  # Hypothesis: reasoning for complex code
        "grok-3",  # Hypothesis: alternative
    ],
}


def get_hypothesized_models_for_task(task_type: str) -> list[str]:
    """Get hypothesized models for a task type.

    WARNING: These are hypotheses to be validated by experiments.
    Use the evaluation framework to find the actual best models.
    """
    return TASK_MODEL_HYPOTHESES.get(task_type, list(MODEL_REGISTRY.keys())[:4])
