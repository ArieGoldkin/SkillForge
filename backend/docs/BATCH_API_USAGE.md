# OpenAI Batch API Integration

**50% cost savings on async operations**

This document describes how to use the OpenAI Batch API integration for non-time-sensitive operations like golden dataset generation and evaluation runs.

## Overview

The Batch API provides:
- **50% cost savings** compared to real-time API
- **No rate limiting** concerns (ideal for large batches)
- **24-hour completion window** (not suitable for real-time workflows)
- **Automatic fallback** to real-time API on failures

## Configuration

Add these settings to your `.env` file:

```bash
# Enable Batch API (default: false)
OPENAI_BATCH_ENABLED=false

# Completion window (only "24h" supported by OpenAI)
OPENAI_BATCH_COMPLETION_WINDOW=24h

# Minimum batch size for using Batch API
# Smaller batches use real-time API to avoid overhead
OPENAI_BATCH_MIN_SIZE=10
```

## Usage Examples

### 1. Batch Embeddings (via EmbeddingService)

```python
from app.shared.services.embeddings.service import EmbeddingService

service = EmbeddingService()

# Generate embeddings with automatic Batch API selection
# Uses Batch API if OPENAI_BATCH_ENABLED=true and len(texts) >= OPENAI_BATCH_MIN_SIZE
texts = ["Document 1", "Document 2", ..., "Document 100"]
results = await service.generate_embeddings_batch(texts)

# Force Batch API usage (regardless of config)
results = await service.generate_embeddings_batch(texts, use_batch_api=True)

# Force real-time API usage
results = await service.generate_embeddings_batch(texts, use_batch_api=False)
```

### 2. Direct Batch Embeddings (Standalone)

```python
from app.shared.services.batch.openai_batch import batch_embeddings

# Direct use of Batch API (bypasses config checks)
texts = ["Document 1", "Document 2", ..., "Document 100"]
embeddings = await batch_embeddings(texts, model="text-embedding-3-small")

# Returns: list[list[float]] (same order as input)
```

### 3. Batch Chat Completions (for Evaluations)

```python
from app.shared.services.batch.openai_batch import batch_chat_completions

# Prepare messages for each completion
messages_list = [
    [{"role": "user", "content": "What is RAG?"}],
    [{"role": "user", "content": "Explain semantic search"}],
    # ... more messages
]

# Generate completions with 50% cost savings
completions = await batch_chat_completions(
    messages_list,
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=500,
)

# Returns: list[str] (completion texts in same order as input)
```

## Integration Points

### Golden Dataset Generation

When generating embeddings for the golden dataset (98 documents, 415 chunks):

```python
# In backup_golden_dataset.py or similar
from app.core.config import settings

# Collect all chunk texts
chunk_texts = [chunk.content for chunk in chunks]

# Generate embeddings with Batch API if enabled
# With OPENAI_BATCH_ENABLED=true, saves 50% on embedding costs
embeddings = await embedding_service.generate_embeddings_batch(
    chunk_texts,
    use_batch_api=settings.OPENAI_BATCH_ENABLED,
)
```

**Cost Comparison (415 chunks):**
- Real-time API: ~$0.008 (assuming 500 tokens/chunk avg)
- Batch API: ~$0.004 (50% savings)

### Evaluation Runs

For quality evaluation or experiments with multiple LLM calls:

```python
from app.shared.services.batch.openai_batch import batch_chat_completions

# Prepare evaluation prompts
eval_prompts = [
    [{"role": "user", "content": f"Evaluate: {finding}"}]
    for finding in findings
]

# Run evaluation with 50% cost savings
results = await batch_chat_completions(
    eval_prompts,
    model="gpt-4o-mini",
    temperature=0.0,  # Deterministic for evaluation
)
```

**Cost Comparison (100 evaluations):**
- Real-time API: ~$0.60 (assuming 1K input + 500 output tokens)
- Batch API: ~$0.30 (50% savings)

## Trade-offs

### When to Use Batch API

✅ **Good for:**
- Golden dataset generation (one-time operation)
- Evaluation runs (can wait 24h for results)
- Experiments and benchmarking
- Bulk processing with no time constraints

❌ **Not suitable for:**
- Real-time user-facing workflows
- Interactive API endpoints
- Time-sensitive operations (<24h deadline)

### Automatic Fallback

The integration includes automatic fallback to real-time API:

```python
# If Batch API fails (network error, timeout, etc.)
# Automatically retries with real-time API
try:
    results = await service.generate_embeddings_batch(texts, use_batch_api=True)
except Exception:
    # Falls back to real-time API automatically
    logger.warning("batch_api_fallback_to_realtime")
    results = await service.generate_embeddings_batch(texts, use_batch_api=False)
```

## Monitoring

Enable metrics to track Batch API usage:

```python
from app.shared.services.metrics import get_metrics_service

metrics = get_metrics_service()

# Metrics are automatically recorded:
# - batch_embeddings_started
# - batch_embeddings_completed
# - batch_completions_started
# - batch_completions_completed
```

## Implementation Details

### File Storage

Batch request files are stored temporarily:
- Location: `/tmp/skillforge_batches/batch_{uuid}.jsonl`
- Format: JSONL (one request per line)
- Cleanup: Managed by OpenAI after processing

### Polling Strategy

```python
# Default polling settings (from openai_batch.py)
poll_interval = 60  # Check every 60 seconds
max_wait = 86400    # Timeout after 24 hours
```

### Error Handling

```python
# Batch API errors are logged with context
logger.exception(
    "batch_api_embeddings_failed",
    error=str(e),
    text_count=len(texts),
)
```

## Cost Savings Examples

### Scenario 1: Golden Dataset (415 chunks)

Assuming average 500 tokens per chunk:
- Total tokens: 415 × 500 = 207,500 tokens
- Real-time cost: $0.00002/1K × 207.5 = $0.00415
- Batch API cost: $0.00001/1K × 207.5 = $0.002075
- **Savings: $0.002075 (50%)**

### Scenario 2: Evaluation Run (1,000 completions)

Assuming 1K input + 500 output tokens per completion:
- Input: 1,000 × 1K = 1M tokens
- Output: 1,000 × 500 = 500K tokens
- Real-time cost: ($0.150/1M × 1) + ($0.600/1M × 0.5) = $0.45
- Batch API cost: ($0.075/1M × 1) + ($0.300/1M × 0.5) = $0.225
- **Savings: $0.225 (50%)**

## References

- [OpenAI Batch API Guide](https://platform.openai.com/docs/guides/batch)
- [Batch API Pricing](https://openai.com/api/pricing/)
- Implementation: `app/shared/services/batch/openai_batch.py`
- Config: `app/core/config.py` (OPENAI_BATCH_* settings)
