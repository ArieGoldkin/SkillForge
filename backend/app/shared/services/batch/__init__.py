"""OpenAI Batch API client for 50% cost savings on async operations.

This module provides batch processing capabilities for OpenAI API operations,
enabling 50% cost savings on non-time-sensitive requests (embeddings, completions).

Key Features:
- Create and upload batch request files (JSONL format)
- Submit batch jobs to OpenAI with metadata tracking
- Poll for completion with configurable timeout
- Download and parse results with error handling
- Helper functions for common batch operations (embeddings)

Usage:
    >>> from app.shared.services.batch import get_batch_client, batch_embeddings
    >>>
    >>> # High-level helper for embeddings
    >>> embeddings = await batch_embeddings(["text1", "text2", ...])
    >>>
    >>> # Low-level batch client for custom operations
    >>> client = get_batch_client()
    >>> file_id = await client.create_batch_file(requests)
    >>> batch_id = await client.submit_batch(file_id)
    >>> results = await client.wait_for_completion(batch_id)

Cost Savings:
    - Batch API: 50% discount vs real-time API
    - text-embedding-3-small: $0.00001/1K tokens (batch) vs $0.00002/1K (real-time)
    - Example: 1M token embeddings = $10 → $5 (batch)

Trade-offs:
    - Completion window: 24 hours (not suitable for real-time needs)
    - Best for: Large-scale dataset processing, evaluation, golden dataset regeneration
    - Not for: User-facing features, real-time analysis workflows

References:
    - OpenAI Batch API: https://platform.openai.com/docs/guides/batch
    - Pricing: https://openai.com/api/pricing/

"""

from app.shared.services.batch.openai_batch import (
    OpenAIBatchClient,
    batch_embeddings,
    get_batch_client,
)

__all__ = [
    "OpenAIBatchClient",
    "batch_embeddings",
    "get_batch_client",
]
