---
name: ai-local-dev
description: Zero-cost AI development with Ollama local inference
version: 1.0.0
type: composite
includes:
  - ai-llm/ollama-local-inference
  - ai-llm/cost-optimization
trigger: "OLLAMA_ENABLED=true"
---

# AI Local Development

Run AI workloads locally with Ollama for zero API cost during development and CI.

## When to Use

- Local development without API costs
- CI/CD pipelines (93% cost savings)
- Privacy-sensitive applications
- Low-latency inference needs

## Cost Comparison

| Environment | Cloud Cost | Local Cost | Savings |
|-------------|------------|------------|---------|
| Development | $500/month | $0 | 100% |
| CI (100 runs) | $200/month | $0 | 100% |
| Production | $2,000/month | $50 (power) | 97.5% |

## Quick Setup

```bash
# Install Ollama
brew install ollama  # macOS

# Start and pull models
brew services start ollama
ollama pull nomic-embed-text      # Embeddings (768 dims)
ollama pull qwen2.5-coder:32b     # Code generation
ollama pull deepseek-r1:70b       # Complex reasoning
```

## Environment Config

```bash
# .env.local
OLLAMA_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_REASONING=deepseek-r1:70b
OLLAMA_MODEL_CODING=qwen2.5-coder:32b
OLLAMA_MODEL_EMBED=nomic-embed-text
```

## Provider Factory

```python
def get_llm_provider(task_type: str = "reasoning"):
    """Auto-switch between local and cloud."""
    if settings.OLLAMA_ENABLED:
        from langchain_ollama import ChatOllama
        models = {
            "reasoning": "deepseek-r1:70b",
            "coding": "qwen2.5-coder:32b"
        }
        return ChatOllama(
            model=models.get(task_type),
            keep_alive="5m"  # Avoid cold starts
        )

    # Cloud fallback
    from langchain.chat_models import init_chat_model
    return init_chat_model("claude-sonnet-4-20250514")
```

## Performance (M4 Max 256GB)

| Model | Tokens/sec | Memory |
|-------|-----------|--------|
| deepseek-r1:70b | 15-20 | ~42GB |
| qwen2.5-coder:32b | 30-40 | ~35GB |
| nomic-embed-text | N/A | ~0.5GB |

## Included Skills

1. **ollama-local-inference** - Setup, LangChain, CI integration
2. **cost-optimization** - Model selection, caching strategies

## See Also

- [ollama-local-inference](../_atomic/ai-llm/ollama-local-inference.md)
- [cost-optimization](../_atomic/ai-llm/cost-optimization.md)
