---
name: ollama-local-inference
description: Run LLMs locally with Ollama for zero API cost
version: 1.0.0
tags: [ai, llm, ollama, local, inference, langchain, ci]
size: atomic
domain: ai-llm
---

# Ollama Local Inference

## Overview

Ollama runs LLMs locally on Apple Silicon and NVIDIA GPUs:
- **93% CI cost savings** vs cloud APIs
- **50-200ms latency** vs 200-500ms cloud
- **Data privacy**: Never leaves your machine

## Model Recommendations

| Task | Model | Size | Performance |
|------|-------|------|-------------|
| Reasoning | `deepseek-r1:70b` | ~42GB | GPT-4 level |
| Coding | `qwen2.5-coder:32b` | ~35GB | 73.7% Aider |
| Embeddings | `nomic-embed-text` | ~0.5GB | 768 dims |

## Quick Start

```bash
# Install
brew install ollama  # macOS
curl -fsSL https://ollama.com/install.sh | sh  # Linux

# Start & pull models
brew services start ollama
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:32b
```

## LangChain Integration

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings

# Chat
llm = ChatOllama(
    model="qwen2.5-coder:32b",
    base_url="http://localhost:11434",
    temperature=0.0,
    keep_alive="5m",  # Keep loaded for 5 min (avoids cold starts)
)

response = await llm.ainvoke("Explain Python decorators")

# Embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector = await embeddings.aembed_query("Hello world")  # 768 dims
```

## Tool Calling

```python
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny, 72F"

llm_with_tools = llm.bind_tools([get_weather])
response = await llm_with_tools.ainvoke("What's the weather in NYC?")
```

## Provider Factory

```python
def get_llm_provider(task_type: str = "reasoning"):
    """Auto-switch between local and cloud."""
    if settings.OLLAMA_ENABLED:
        from langchain_ollama import ChatOllama
        models = {"reasoning": "deepseek-r1:70b", "coding": "qwen2.5-coder:32b"}
        return ChatOllama(model=models.get(task_type), keep_alive="5m")

    # Cloud fallback
    from langchain.chat_models import init_chat_model
    return init_chat_model("claude-sonnet-4-20250514")
```

## CI Integration

```yaml
# GitHub Actions (self-hosted runner)
jobs:
  test:
    runs-on: self-hosted  # M4 Max 256GB
    env:
      OLLAMA_ENABLED: "true"
      OLLAMA_HOST: "http://localhost:11434"
    steps:
      - name: Ensure Ollama ready
        run: |
          until curl -s http://localhost:11434/api/tags > /dev/null; do
            sleep 2
          done
          # Pre-warm
          curl -s http://localhost:11434/api/embeddings \
            -d '{"model":"nomic-embed-text","prompt":"warmup"}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "connection refused" | `brew services start ollama` |
| "model not found" | `ollama pull <model>` |
| Slow first request | Use `keep_alive="5m"` and pre-warm |
| Out of memory | Use smaller model or quantized version |

## Performance (M4 Max 256GB)

| Model | Tokens/sec | First Token | Memory |
|-------|-----------|-------------|--------|
| deepseek-r1:70b | 15-20 | 2-3s | ~42GB |
| qwen2.5-coder:32b | 30-40 | 1-2s | ~35GB |
| nomic-embed-text | N/A | ~50ms | ~0.5GB |

**Cold start**: +30-60 seconds
**Warm start**: ~50-200ms
