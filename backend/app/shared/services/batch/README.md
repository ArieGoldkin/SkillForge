# OpenAI Batch API Client

Production-ready client for OpenAI's Batch API, enabling **50% cost savings** on non-time-sensitive operations.

## Cost Savings

| Operation | Real-time API | Batch API | Savings |
|-----------|--------------|-----------|---------|
| text-embedding-3-small | $0.00002/1K tokens | $0.00001/1K tokens | 50% |
| gpt-4o-mini | $0.15/$0.60 per 1M tokens | $0.075/$0.30 per 1M tokens | 50% |
| gpt-4o | $2.50/$10.00 per 1M tokens | $1.25/$5.00 per 1M tokens | 50% |

**Example:** Embedding 1M tokens costs $20 real-time vs $10 batch = **$10 saved** (50%)

## When to Use Batch API

### ✅ Good Use Cases
- **Golden dataset regeneration** - Regenerate embeddings for 98 documents overnight
- **Evaluation datasets** - Generate embeddings for test sets (not time-sensitive)
- **Bulk content processing** - Process large document collections
- **Offline analysis** - Generate reports, summaries, comparisons
- **Data migrations** - Re-embed content after model upgrades

### ❌ Bad Use Cases
- **User-facing features** - Real-time analysis workflow (need immediate results)
- **Interactive chat** - Tutor sessions (users expect instant responses)
- **Real-time search** - Query-time embeddings (latency-sensitive)
- **Time-critical alerts** - Monitoring, notifications

## Trade-offs

| Aspect | Real-time API | Batch API |
|--------|--------------|-----------|
| **Cost** | 2x price | 50% discount |
| **Latency** | Seconds | Up to 24 hours |
| **Rate limits** | Strict (RPM/TPM) | None |
| **Use case** | Production features | Offline processing |

## Quick Start

### High-Level Helper (Recommended)

```python
from app.shared.services.batch import batch_embeddings

# Generate embeddings for list of texts
texts = ["Document 1", "Document 2", "Document 3", ...]
embeddings = await batch_embeddings(texts)

# Result: List of 1536-dimensional vectors (same order as input)
print(f"Generated {len(embeddings)} embeddings")
```

### Low-Level Client (Advanced)

```python
from app.shared.services.batch import get_batch_client

client = get_batch_client()

# 1. Create batch file
requests = [
    {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]},
    {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "World"}]},
]
file_id = await client.create_batch_file(requests)

# 2. Submit batch job
batch_id = await client.submit_batch(
    file_id,
    metadata={"dataset": "golden", "task": "evaluation"}
)

# 3. Wait for completion (polls every 60s)
status = await client.wait_for_completion(batch_id)

# 4. Get results
results = await client.get_batch_results(batch_id)
for result in results:
    if "error" in result:
        print(f"Request {result['custom_id']} failed: {result['error']}")
    else:
        print(f"Response: {result['response']['body']}")
```

## Real-World Example: Golden Dataset Regeneration

```python
"""Regenerate embeddings for golden dataset using Batch API (50% savings)."""

from app.db.repositories.chunk_repository import ChunkRepository
from app.shared.services.batch import batch_embeddings

async def regenerate_golden_embeddings():
    """Regenerate embeddings for 415 chunks using Batch API."""

    # 1. Fetch all golden chunks
    repo = ChunkRepository(db_session)
    chunks = await repo.get_all_golden_chunks()

    print(f"Regenerating embeddings for {len(chunks)} chunks...")

    # 2. Extract text content
    texts = [chunk.content for chunk in chunks]

    # 3. Generate embeddings via Batch API (50% cost savings)
    embeddings = await batch_embeddings(texts, model="text-embedding-3-small")

    # 4. Update database
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
        await repo.update(chunk)

    print(f"✅ Updated {len(chunks)} embeddings")
    print(f"💰 Cost savings: ~50% vs real-time API")
```

**Cost Analysis:**
- 415 chunks × ~500 tokens/chunk = 207,500 tokens
- Real-time: $0.00002/1K × 207.5 = **$0.00415**
- Batch API: $0.00001/1K × 207.5 = **$0.002075** (50% savings)

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
BATCH_POLL_INTERVAL=60  # Seconds between status checks
BATCH_MAX_WAIT=86400    # Maximum wait time (24 hours)
```

### Batch Directory

Temporary batch files are stored in `/tmp/skillforge_batches/`:
- Created automatically on first use
- Files are uploaded to OpenAI and can be deleted locally
- Not tracked in git (add to `.gitignore` if needed)

## Error Handling

```python
from app.shared.services.batch import batch_embeddings

try:
    embeddings = await batch_embeddings(texts)
except ValueError as e:
    # Empty text list, invalid input
    print(f"Validation error: {e}")
except TimeoutError as e:
    # Batch didn't complete within 24 hours
    print(f"Timeout: {e}")
except RuntimeError as e:
    # Individual request failed
    print(f"Embedding failed: {e}")
except Exception as e:
    # OpenAI API error, network issue
    print(f"Unexpected error: {e}")
```

## Monitoring & Observability

All batch operations are logged via structlog:

```python
# Batch file created
logger.info("batch_file_created", file_id="file-123", request_count=100)

# Batch submitted
logger.info("batch_submitted", batch_id="batch-456", status="validating")

# Polling progress
logger.info("batch_polling", batch_id="batch-456", completed=50, total=100)

# Completion
logger.info("batch_completed", batch_id="batch-456", final_status="completed")
```

## API Reference

### `batch_embeddings(texts, model="text-embedding-3-small")`

High-level helper for batch embedding generation.

**Parameters:**
- `texts` (list[str]): List of text strings to embed
- `model` (str): OpenAI embedding model (default: text-embedding-3-small)

**Returns:**
- `list[list[float]]`: List of embedding vectors (same order as input)

**Raises:**
- `ValueError`: Empty text list
- `TimeoutError`: Batch didn't complete within 24 hours
- `RuntimeError`: Individual request failed

### `OpenAIBatchClient`

Low-level client for batch operations.

#### `create_batch_file(requests, endpoint="/v1/chat/completions")`

Create JSONL batch file and upload to OpenAI.

**Parameters:**
- `requests` (list[dict]): List of API request bodies
- `endpoint` (BatchEndpoint): API endpoint (chat, embeddings, completions, moderations)

**Returns:**
- `str`: OpenAI file ID

#### `submit_batch(file_id, endpoint, completion_window="24h", metadata=None)`

Submit batch job to OpenAI.

**Parameters:**
- `file_id` (str): File ID from `create_batch_file()`
- `endpoint` (BatchEndpoint): API endpoint
- `completion_window` (CompletionWindow): "24h" (only option)
- `metadata` (dict[str, str] | None): Optional metadata (max 16 key-value pairs)

**Returns:**
- `str`: Batch job ID

#### `get_batch_status(batch_id)`

Get current batch status and progress.

**Returns:**
- `dict[str, Any]`: Status dictionary with id, status, request_counts, output_file_id, error_file_id

#### `wait_for_completion(batch_id, poll_interval=60, max_wait=86400)`

Poll until batch completes or times out.

**Parameters:**
- `batch_id` (str): Batch job ID
- `poll_interval` (int): Seconds between checks (default: 60)
- `max_wait` (int): Maximum wait seconds (default: 86400 = 24 hours)

**Returns:**
- `dict[str, Any]`: Final status dictionary

#### `get_batch_results(batch_id)`

Download and parse batch results.

**Returns:**
- `list[dict[str, Any]]`: List of result dictionaries

## Testing

```bash
# Run batch client tests
cd backend
poetry run pytest tests/unit/shared/services/batch/ -v

# Run with coverage
poetry run pytest tests/unit/shared/services/batch/ --cov=app.shared.services.batch
```

**Test Coverage:** 30 tests covering:
- Batch file creation and upload
- Job submission with metadata
- Status polling and completion
- Result download and parsing
- Error handling and validation
- Helper functions (batch_embeddings)

## Best Practices

1. **Use batch_embeddings() for simple cases** - Handles all complexity internally
2. **Add metadata for tracking** - Helps identify batches later
3. **Monitor batch status** - Check Langfuse or logs for progress
4. **Handle errors gracefully** - Individual requests can fail independently
5. **Don't block on batch completion** - Submit batch and check later
6. **Clean up old batches** - Files are deleted after 7 days by OpenAI

## Future Enhancements

- [ ] Batch chat completions support (gpt-4o-mini, gpt-4o)
- [ ] Retry logic for failed requests
- [ ] Batch status webhooks (avoid polling)
- [ ] Cost tracking and reporting
- [ ] Integration with Langfuse for observability

## References

- [OpenAI Batch API Documentation](https://platform.openai.com/docs/guides/batch)
- [Batch API Pricing](https://openai.com/api/pricing/)
- [Batch API Reference](https://platform.openai.com/docs/api-reference/batch)
