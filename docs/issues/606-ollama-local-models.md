# Issue #606: Ollama Local Models for CI Cost Reduction

**Status:** In Progress
**PR:** [#607](https://github.com/ArieGoldkin/SkillForge/pull/607)
**Branch:** `issue/606-ollama-local-models`

## Summary

Add Ollama local model support for 93% CI cost reduction on self-hosted Apple Silicon runners.

## Changes

### New Files
- `backend/app/shared/services/llm/ollama_provider.py` - LangChain-compatible Ollama provider
- `backend/app/shared/services/llm/factory.py` - Cloud/local provider factory
- `backend/app/shared/services/embeddings/ollama_service.py` - Ollama embeddings
- `backend/tests/unit/services/llm/test_*.py` - Unit tests

### Modified Files
- `backend/app/core/config.py` - Ollama settings (OLLAMA_ENABLED, OLLAMA_HOST, etc.)
- `backend/app/core/model_registry.py` - Ollama models in registry
- `.github/workflows/evaluation.yml` - CI uses Ollama when available

## Models

| Model | Use Case | Size |
|-------|----------|------|
| `deepseek-r1:70b` | Reasoning, G-Eval | ~42GB Q4 |
| `qwen2.5-coder:32b` | Coding, agents | ~35GB Q8 |
| `nomic-embed-text` | Embeddings | ~0.5GB |

## Environment Variables

```bash
OLLAMA_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_REASONING=deepseek-r1:70b
OLLAMA_MODEL_CODING=qwen2.5-coder:32b
OLLAMA_MODEL_EMBED=nomic-embed-text
```

## Testing

```bash
# Run Ollama provider tests
cd backend && poetry run pytest tests/unit/services/llm/ -v

# Run with Ollama enabled
OLLAMA_ENABLED=true poetry run pytest tests/unit/ -v
```

## Cost Impact

- **Before:** ~$50-100/month on cloud LLM APIs for CI
- **After:** $0 (local inference on M4 Max runner)
- **Savings:** 93%+ reduction
