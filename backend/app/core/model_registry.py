"""Model registry with December 2025 LLM pricing and capabilities.

This module provides a centralized registry of all supported LLM models
with their pricing, capabilities, and metadata for evaluation-driven
model selection.

Sources (Dec 2025):
- Anthropic API Docs: https://docs.anthropic.com/en/docs/about-claude/models
- Google AI: https://ai.google.dev/pricing
- OpenAI: https://platform.openai.com/docs/models
- DeepSeek: https://api-docs.deepseek.com/
- xAI: https://docs.x.ai/docs
- OpenRouter aggregation for cross-validation
"""

from dataclasses import dataclass
from typing import Final, Literal

LatencyTier = Literal["fast", "medium", "slow"]
Provider = Literal["openai", "anthropic", "google_genai", "xai", "deepseek", "ollama"]


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
# DECEMBER 2025 MODEL REGISTRY (Updated Dec 18, 2025)
# =============================================================================

MODEL_REGISTRY: Final[dict[str, ModelInfo]] = {
    # =========================================================================
    # ANTHROPIC MODELS - Claude 4.5 Series (Latest)
    # =========================================================================
    "claude-opus-4-5-20251101": ModelInfo(
        provider="anthropic",
        model_id="claude-opus-4-5-20251101",
        display_name="Claude Opus 4.5",
        input_cost_per_1m=5.00,
        output_cost_per_1m=25.00,
        context_window=200_000,
        latency_tier="slow",
        capabilities=("top_reasoning", "coding", "agents", "architecture"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="Nov 2025, highest intelligence, May 2025 knowledge cutoff",
    ),
    "claude-sonnet-4-5-20250929": ModelInfo(
        provider="anthropic",
        model_id="claude-sonnet-4-5-20250929",
        display_name="Claude Sonnet 4.5",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=200_000,  # 1M beta with header
        latency_tier="medium",
        capabilities=("coding", "agents", "reasoning", "synthesis"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="Sep 2025, excellent coding, 1M beta available",
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
        notes="May 2025, SWE-bench leader (72.5%)",
    ),
    "claude-haiku-4-5-20251001": ModelInfo(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        input_cost_per_1m=1.00,
        output_cost_per_1m=5.00,
        context_window=200_000,
        latency_tier="fast",
        capabilities=("fast", "balanced", "coding", "classification"),
        api_key_field="ANTHROPIC_API_KEY",
        notes="Oct 2025, fastest Claude, extended thinking capable",
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
        notes="Oct 2024, legacy but still cheap and reliable",
    ),
    # =========================================================================
    # GOOGLE MODELS - Gemini 3.0 & 2.5 Series
    # =========================================================================
    "gemini-3-pro": ModelInfo(
        provider="google_genai",
        model_id="gemini-3-pro-preview",
        display_name="Gemini 3 Pro",
        input_cost_per_1m=2.00,
        output_cost_per_1m=12.00,
        context_window=1_000_000,
        latency_tier="medium",
        capabilities=("top_reasoning", "multimodal", "long_context"),
        api_key_field="GOOGLE_API_KEY",
        notes="Dec 2025 preview, best multimodal understanding",
    ),
    "gemini-3-flash": ModelInfo(
        provider="google_genai",
        model_id="gemini-3-flash-preview",
        display_name="Gemini 3 Flash",
        input_cost_per_1m=0.50,
        output_cost_per_1m=3.00,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("reasoning", "coding", "agents", "multimodal"),
        api_key_field="GOOGLE_API_KEY",
        notes="Dec 2025 preview, 78% SWE-bench, frontier at Flash speed",
    ),
    "gemini-2.5-pro": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        context_window=1_000_000,
        latency_tier="medium",
        capabilities=("reasoning", "multimodal", "long_context", "coding"),
        api_key_field="GOOGLE_API_KEY",
        notes="1M context, good for long document analysis",
    ),
    "gemini-2.5-flash": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        input_cost_per_1m=0.30,
        output_cost_per_1m=2.50,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("fast", "multimodal", "balanced", "synthesis"),
        api_key_field="GOOGLE_API_KEY",
        notes="Cost-effective 1M context, good for synthesis",
    ),
    "gemini-2.5-flash-lite": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.5-flash-lite",
        display_name="Gemini 2.5 Flash-Lite",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("fast", "classification", "routing", "simple"),
        api_key_field="GOOGLE_API_KEY",
        notes="Ultra-cheap 1M context, best for supervisor routing",
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
        notes="Previous gen, cheap and reliable",
    ),
    "gemini-2.0-flash-lite": ModelInfo(
        provider="google_genai",
        model_id="gemini-2.0-flash-lite",
        display_name="Gemini 2.0 Flash-Lite",
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        context_window=1_000_000,
        latency_tier="fast",
        capabilities=("fast", "simple", "classification"),
        api_key_field="GOOGLE_API_KEY",
        notes="Cheapest 1M context model available",
    ),
    # =========================================================================
    # OPENAI MODELS - GPT-5 Series
    # =========================================================================
    "gpt-5": ModelInfo(
        provider="openai",
        model_id="gpt-5-high",
        display_name="GPT-5",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        context_window=400_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "agents", "multimodal"),
        api_key_field="OPENAI_API_KEY",
        notes="400K context, strong reasoning",
    ),
    "gpt-5-mini": ModelInfo(
        provider="openai",
        model_id="gpt-5-mini-high",
        display_name="GPT-5 Mini",
        input_cost_per_1m=0.25,
        output_cost_per_1m=2.00,
        context_window=400_000,
        latency_tier="fast",
        capabilities=("balanced", "coding", "general"),
        api_key_field="OPENAI_API_KEY",
        notes="Compact reasoning, good balance",
    ),
    "gpt-4o": ModelInfo(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        context_window=128_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "multimodal", "vision"),
        api_key_field="OPENAI_API_KEY",
        notes="Multimodal with vision, still widely used",
    ),
    "gpt-4o-mini": ModelInfo(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        context_window=128_000,
        latency_tier="fast",
        capabilities=("balanced", "coding", "multimodal"),
        api_key_field="OPENAI_API_KEY",
        notes="Reliable and cheap, good fallback",
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
        notes="Reasoning specialist, slower but thorough",
    ),
    # =========================================================================
    # XAI MODELS - Grok 4.1 Series
    # =========================================================================
    "grok-4.1-fast": ModelInfo(
        provider="xai",
        model_id="grok-4.1-fast",
        display_name="Grok 4.1 Fast",
        input_cost_per_1m=0.20,
        output_cost_per_1m=0.50,
        context_window=2_000_000,
        latency_tier="fast",
        capabilities=("long_context", "agents", "synthesis", "tool_calling"),
        api_key_field="XAI_API_KEY",
        notes="2M context at $0.20/$0.50 - best for massive docs",
    ),
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
    # =========================================================================
    # DEEPSEEK MODELS - V3.2 (Ultra-Cheap)
    # =========================================================================
    "deepseek-v3": ModelInfo(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek V3.2",
        input_cost_per_1m=0.14,
        output_cost_per_1m=0.28,
        context_window=64_000,
        latency_tier="fast",
        capabilities=("reasoning", "coding", "cost_effective", "classification"),
        api_key_field="DEEPSEEK_API_KEY",
        notes="236B params at $0.14/$0.28 - cheapest quality model",
    ),
    "deepseek-reasoner": ModelInfo(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek V3.2 Reasoner",
        input_cost_per_1m=0.26,
        output_cost_per_1m=0.38,
        context_window=64_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "thinking"),
        api_key_field="DEEPSEEK_API_KEY",
        notes="Thinking/reasoning mode for complex tasks",
    ),
    # =========================================================================
    # OLLAMA LOCAL MODELS - Zero Cost (Issue #606)
    # =========================================================================
    "ollama-deepseek-r1-70b": ModelInfo(
        provider="ollama",
        model_id="deepseek-r1:70b",
        display_name="DeepSeek R1 70B (Local)",
        input_cost_per_1m=0.0,  # FREE - local inference
        output_cost_per_1m=0.0,
        context_window=64_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "thinking", "agents"),
        api_key_field="",  # No API key needed
        notes="MIT license, matches GPT-4/o1 level, ~42GB Q4 quantized",
    ),
    "ollama-qwen25-coder-32b": ModelInfo(
        provider="ollama",
        model_id="qwen2.5-coder:32b",
        display_name="Qwen 2.5 Coder 32B (Local)",
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        context_window=32_768,
        latency_tier="fast",
        capabilities=("coding", "agents", "classification", "synthesis"),
        api_key_field="",
        notes="73.7% Aider benchmark (≈ GPT-4o), ~35GB Q8 quantized",
    ),
    "ollama-llama33-70b": ModelInfo(
        provider="ollama",
        model_id="llama3.3:70b",
        display_name="Llama 3.3 70B (Local)",
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        context_window=128_000,
        latency_tier="medium",
        capabilities=("reasoning", "coding", "agents", "multimodal"),
        api_key_field="",
        notes="Meta's latest, ~40GB Q4 quantized, good general purpose",
    ),
    "ollama-nomic-embed": ModelInfo(
        provider="ollama",
        model_id="nomic-embed-text",
        display_name="Nomic Embed v1.5 (Local)",
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        context_window=8_192,
        latency_tier="fast",
        capabilities=("embeddings", "fast"),
        api_key_field="",
        notes="768 dimensions, ~0.5GB, good for CI evaluation",
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
    return [name for name, info in MODEL_REGISTRY.items() if capability in info.capabilities]


def list_models_by_latency(tier: LatencyTier) -> list[str]:
    """List all models in a latency tier."""
    return [name for name, info in MODEL_REGISTRY.items() if info.latency_tier == tier]


def get_cheapest_models(top_n: int = 5) -> list[tuple[str, float]]:
    """Get the N cheapest models by estimated cost (1K input + 1K output)."""
    costs = []
    for name, info in MODEL_REGISTRY.items():
        cost = info.estimate_cost(1000, 1000)
        costs.append((name, cost))
    return sorted(costs, key=lambda x: x[1])[:top_n]


def get_available_models(settings: object) -> list[str]:
    """Get models that have API keys configured."""
    available = []
    for name, info in MODEL_REGISTRY.items():
        api_key = getattr(settings, info.api_key_field, None)
        if api_key:
            available.append(name)
    return available


# =============================================================================
# TASK-BASED MODEL RECOMMENDATIONS (Dec 2025 - Cost-Optimized)
# =============================================================================

TASK_MODEL_HYPOTHESES: Final[dict[str, list[str]]] = {
    # Supervisor: fast classification, 1M context not needed
    "supervisor": [
        "gemini-2.5-flash-lite",  # $0.10/$0.40, 1M ctx - BEST VALUE
        "deepseek-v3",  # $0.14/$0.28, 64K ctx - cheapest
        "gpt-4o-mini",  # $0.15/$0.60 - reliable fallback
        "claude-haiku-3-5-20241022",  # $0.80/$4.00 - quality fallback
    ],
    # G-Eval judging: needs reasoning, quality matters
    "g_eval": [
        "gemini-3-flash",  # $0.50/$3.00, 1M ctx - BEST for eval
        "claude-sonnet-4-20250514",  # $3.00/$15.00 - premium quality
        "gemini-2.5-pro",  # $1.25/$10.00 - long context eval
        "gpt-5-mini",  # $0.25/$2.00 - balanced
    ],
    # Agent analysis: reasoning + domain knowledge
    "agent_analysis": [
        "gemini-2.5-flash",  # $0.30/$2.50, 1M ctx - cost-effective
        "claude-sonnet-4-20250514",  # $3.00/$15.00 - quality
        "gpt-5-mini",  # $0.25/$2.00 - balanced
        "deepseek-v3",  # $0.14/$0.28 - budget option
    ],
    # Synthesis: long context, summarization
    "synthesis": [
        "grok-4.1-fast",  # $0.20/$0.50, 2M ctx - MASSIVE docs
        "gemini-2.5-flash",  # $0.30/$2.50, 1M ctx - balanced
        "claude-sonnet-4-5-20250929",  # $3.00/$15.00 - quality synthesis
        "gemini-2.5-pro",  # $1.25/$10.00 - comprehensive
    ],
    # Tutoring: explanation quality
    "tutoring": [
        "claude-sonnet-4-20250514",  # Best for teaching
        "gemini-3-flash",  # Good explanations + cheap
        "gpt-5",  # Versatile
        "grok-3",  # Conversational
    ],
    # Code analysis: deep code understanding
    "code_analysis": [
        "claude-sonnet-4-20250514",  # SWE-bench leader
        "gemini-3-flash",  # 78% SWE-bench
        "gpt-5",  # Strong at code
        "o3-mini",  # Reasoning for complex code
    ],
}


def get_hypothesized_models_for_task(task_type: str) -> list[str]:
    """Get hypothesized models for a task type.

    WARNING: These are hypotheses to be validated by experiments.
    Use the evaluation framework to find the actual best models.
    """
    return TASK_MODEL_HYPOTHESES.get(task_type, list(MODEL_REGISTRY.keys())[:4])


def list_ollama_models() -> list[str]:
    """List all Ollama local models."""
    return [name for name, info in MODEL_REGISTRY.items() if info.provider == "ollama"]


# =============================================================================
# LOCAL CI MODEL RECOMMENDATIONS (Issue #606)
# =============================================================================

LOCAL_CI_MODEL_MAPPING: Final[dict[str, str]] = {
    # Maps cloud task types to recommended local Ollama models
    "supervisor": "ollama-qwen25-coder-32b",  # Fast classification
    "g_eval": "ollama-deepseek-r1-70b",  # Reasoning for quality eval
    "agent_analysis": "ollama-qwen25-coder-32b",  # Code/domain analysis
    "synthesis": "ollama-deepseek-r1-70b",  # Complex summarization
    "reranker": "ollama-qwen25-coder-32b",  # Fast scoring
    "embeddings": "ollama-nomic-embed",  # Local embeddings
}
