"""Constants for tracing and observability.

2025 Best Practice: Centralize pricing and tracing configuration for
consistent cost tracking across LLM providers.
"""

# LLM Pricing per 1M tokens (USD)
# Updated January 2025 - Anthropic Claude 3.5 Sonnet pricing
LLM_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-2024-04-09": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = {"input": 1.00, "output": 2.00}


def calculate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for LLM usage.

    Args:
        model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated

    Returns:
        Total cost in USD (rounded to 6 decimal places)

    Example:
        >>> calculate_llm_cost("claude-3-5-sonnet-20241022", 1000, 500)
        0.0105  # (1000/1M * 3.00) + (500/1M * 15.00)

    """
    pricing = LLM_PRICING.get(model, DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


# Trace tags for categorization in Langfuse UI
TRACE_TAGS = {
    "parsing": "Content parsing and extraction",
    "validation": "Schema and data validation",
    "llm_call": "LLM API invocations",
    "retry": "Retry and recovery logic",
    "db_query": "Database operations",
    "sse_event": "Server-sent events",
    "self_correction": "Agent self-correction loops",
    "result_processing": "Agent result processing and persistence",
    "specificity": "Specificity scoring and quality assessment",
}
