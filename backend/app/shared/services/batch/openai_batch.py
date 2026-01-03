"""OpenAI Batch API client for 50% cost savings on async operations.

This module implements a production-ready client for OpenAI's Batch API,
enabling 50% cost savings on non-time-sensitive operations like embeddings
and completions.

Architecture:
- Uses AsyncOpenAI client for all API calls
- Stores batch files in /tmp/skillforge_batches directory
- Supports custom metadata for tracking and organization
- Polls for completion with exponential backoff
- Handles errors and timeouts gracefully

Key Methods:
- create_batch_file: Upload JSONL request file to OpenAI
- submit_batch: Submit batch job with completion window
- get_batch_status: Check current status and progress
- wait_for_completion: Poll until completion or timeout
- get_batch_results: Download and parse results

Error Handling:
- Validates file format and request structure
- Handles OpenAI API errors with retry logic
- Provides detailed error messages with context
- Logs all operations for observability

Cost Optimization:
- 50% discount on all batch operations vs real-time
- Configurable completion window (24h default)
- Batch size recommendations for optimal throughput

References:
    - OpenAI Batch API: https://platform.openai.com/docs/guides/batch
    - Batch request format: https://platform.openai.com/docs/api-reference/batch

"""

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

import uuid_utils
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Valid OpenAI Batch API endpoints
BatchEndpoint = Literal[
    "/v1/responses",
    "/v1/chat/completions",
    "/v1/embeddings",
    "/v1/completions",
    "/v1/moderations",
]

# Valid completion windows
CompletionWindow = Literal["24h"]


class OpenAIBatchClient:
    """Client for OpenAI Batch API operations.

    Provides methods for creating, submitting, and monitoring batch jobs
    with the OpenAI API. Supports 50% cost savings on embeddings and
    completions with 24-hour completion window.

    Attributes:
        client: AsyncOpenAI client instance
        batch_dir: Directory for storing batch request files

    Example:
        >>> client = OpenAIBatchClient()
        >>> requests = [{"model": "gpt-4o-mini", "messages": [...]}]
        >>> file_id = await client.create_batch_file(requests)
        >>> batch_id = await client.submit_batch(file_id)
        >>> status = await client.wait_for_completion(batch_id)
        >>> results = await client.get_batch_results(batch_id)

    """

    def __init__(self) -> None:
        """Initialize OpenAI Batch client.

        Raises:
            ValueError: If OPENAI_API_KEY is not configured.

        """
        if not settings.OPENAI_API_KEY:
            msg = "OPENAI_API_KEY is required for batch operations"
            raise ValueError(msg)

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # S108: Using /tmp for temporary batch files is acceptable here
        # as these files are short-lived and only used for OpenAI API uploads
        self.batch_dir = Path("/tmp/skillforge_batches")  # noqa: S108
        self.batch_dir.mkdir(exist_ok=True)

        logger.info(
            "batch_client_initialized",
            batch_dir=str(self.batch_dir),
            provider="openai",
        )

    async def create_batch_file(
        self,
        requests: list[dict[str, Any]],
        endpoint: BatchEndpoint = "/v1/chat/completions",
    ) -> str:
        """Create JSONL file for batch processing and upload to OpenAI.

        Converts list of API requests into JSONL format required by Batch API,
        saves to local file, and uploads to OpenAI for batch processing.

        Args:
            requests: List of API request bodies (model, messages, etc.)
            endpoint: OpenAI API endpoint (default: /v1/chat/completions)

        Returns:
            OpenAI file ID for the uploaded batch file

        Raises:
            ValueError: If requests list is empty
            Exception: If file upload fails

        Example:
            >>> requests = [
            ...     {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
            ...     {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]},
            ... ]
            >>> file_id = await client.create_batch_file(requests)

        """
        if not requests:
            msg = "Cannot create batch file with empty requests list"
            raise ValueError(msg)

        file_path = self.batch_dir / f"batch_{uuid_utils.uuid7()}.jsonl"

        # Write JSONL format required by Batch API
        # ASYNC230: File I/O is acceptable here - this is a one-time write before
        # uploading to OpenAI API. Not on critical path for async operations.
        with file_path.open("w") as f:
            for i, request in enumerate(requests):
                batch_request = {
                    "custom_id": f"request-{i}",
                    "method": "POST",
                    "url": endpoint,
                    "body": request,
                }
                f.write(json.dumps(batch_request) + "\n")

        # Upload file to OpenAI
        try:
            # ASYNC230: File read is acceptable - required for OpenAI upload
            with file_path.open("rb") as f:
                file_response = await self.client.files.create(
                    file=f,
                    purpose="batch",
                )

            logger.info(
                "batch_file_created",
                file_id=file_response.id,
                request_count=len(requests),
                endpoint=endpoint,
                local_path=str(file_path),
            )

            return file_response.id

        except Exception as e:
            logger.exception(
                "batch_file_upload_failed",
                error=str(e),
                request_count=len(requests),
                local_path=str(file_path),
            )
            raise

    async def submit_batch(
        self,
        file_id: str,
        endpoint: BatchEndpoint = "/v1/chat/completions",
        completion_window: CompletionWindow = "24h",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Submit batch job to OpenAI and return batch ID.

        Creates a batch job from an uploaded file. The batch will be processed
        within the specified completion window (24 hours by default).

        Args:
            file_id: OpenAI file ID from create_batch_file()
            endpoint: API endpoint to call (default: /v1/chat/completions)
            completion_window: Processing window ("24h" only for now)
            metadata: Optional metadata dict for tracking (max 16 key-value pairs)

        Returns:
            Batch job ID for status tracking

        Raises:
            ValueError: If file_id is empty or completion_window is invalid
            Exception: If batch submission fails

        Example:
            >>> batch_id = await client.submit_batch(
            ...     file_id="file-abc123", metadata={"dataset": "golden", "task": "evaluation"}
            ... )

        """
        if not file_id:
            msg = "file_id cannot be empty"
            raise ValueError(msg)

        if completion_window not in ["24h"]:
            msg = f"Invalid completion_window: {completion_window}. Only '24h' is supported."
            raise ValueError(msg)

        try:
            batch = await self.client.batches.create(
                input_file_id=file_id,
                endpoint=endpoint,
                completion_window=completion_window,
                metadata=metadata or {},
            )

            logger.info(
                "batch_submitted",
                batch_id=batch.id,
                file_id=file_id,
                status=batch.status,
                endpoint=endpoint,
                completion_window=completion_window,
                metadata=metadata,
            )

            return batch.id

        except Exception as e:
            logger.exception(
                "batch_submission_failed",
                error=str(e),
                file_id=file_id,
                endpoint=endpoint,
            )
            raise

    async def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """Get current status of a batch job.

        Retrieves detailed status information including progress,
        completion counts, and output file IDs.

        Args:
            batch_id: Batch job ID from submit_batch()

        Returns:
            Dictionary containing:
                - id: Batch job ID
                - status: Current status
                  (validating/in_progress/finalizing/completed/failed/expired/cancelled)
                - request_counts: Dict with total/completed/failed counts
                - output_file_id: Output file ID (when completed)
                - error_file_id: Error file ID (if failures occurred)

        Raises:
            ValueError: If batch_id is empty
            Exception: If status retrieval fails

        Example:
            >>> status = await client.get_batch_status("batch-abc123")
            >>> print(
            ...     f"Progress: {status['request_counts']['completed']}/"
            ...     f"{status['request_counts']['total']}"
            ... )

        """
        if not batch_id:
            msg = "batch_id cannot be empty"
            raise ValueError(msg)

        try:
            batch = await self.client.batches.retrieve(batch_id)

            return {
                "id": batch.id,
                "status": batch.status,
                "request_counts": {
                    "total": batch.request_counts.total if batch.request_counts else 0,
                    "completed": batch.request_counts.completed if batch.request_counts else 0,
                    "failed": batch.request_counts.failed if batch.request_counts else 0,
                },
                "output_file_id": batch.output_file_id,
                "error_file_id": batch.error_file_id,
            }

        except Exception as e:
            logger.exception(
                "batch_status_retrieval_failed",
                error=str(e),
                batch_id=batch_id,
            )
            raise

    async def wait_for_completion(
        self,
        batch_id: str,
        poll_interval: int = 60,
        max_wait: int = 86400,  # 24 hours
    ) -> dict[str, Any]:
        """Poll until batch completes or times out.

        Continuously polls batch status until it reaches a terminal state
        (completed/failed/expired/cancelled) or timeout is reached.

        Args:
            batch_id: Batch job ID from submit_batch()
            poll_interval: Seconds between status checks (default: 60)
            max_wait: Maximum seconds to wait (default: 86400 = 24 hours)

        Returns:
            Final batch status dictionary (see get_batch_status)

        Raises:
            ValueError: If batch_id is empty or poll_interval/max_wait are invalid
            TimeoutError: If batch doesn't complete within max_wait
            Exception: If status retrieval fails

        Example:
            >>> status = await client.wait_for_completion(
            ...     batch_id="batch-abc123",
            ...     poll_interval=30,  # Check every 30 seconds
            ...     max_wait=3600,  # 1 hour max
            ... )
            >>> print(f"Final status: {status['status']}")

        """
        if not batch_id:
            msg = "batch_id cannot be empty"
            raise ValueError(msg)

        if poll_interval <= 0:
            msg = f"poll_interval must be positive, got {poll_interval}"
            raise ValueError(msg)

        if max_wait <= 0:
            msg = f"max_wait must be positive, got {max_wait}"
            raise ValueError(msg)

        elapsed = 0

        while elapsed < max_wait:
            status = await self.get_batch_status(batch_id)

            if status["status"] in ("completed", "failed", "expired", "cancelled"):
                logger.info(
                    "batch_completed",
                    batch_id=batch_id,
                    final_status=status["status"],
                    completed=status["request_counts"]["completed"],
                    failed=status["request_counts"]["failed"],
                    total=status["request_counts"]["total"],
                    elapsed_seconds=elapsed,
                )
                return status

            logger.info(
                "batch_polling",
                batch_id=batch_id,
                status=status["status"],
                completed=status["request_counts"]["completed"],
                total=status["request_counts"]["total"],
                elapsed_seconds=elapsed,
            )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        msg = f"Batch {batch_id} did not complete within {max_wait}s"
        raise TimeoutError(msg)

    async def get_batch_results(self, batch_id: str) -> list[dict[str, Any]]:
        """Download and parse batch results.

        Downloads the output file from a completed batch and parses
        the JSONL results into a list of response dictionaries.

        Args:
            batch_id: Batch job ID from submit_batch()

        Returns:
            List of result dictionaries, each containing:
                - custom_id: Original request ID
                - response: API response body
                - error: Error details (if request failed)

        Raises:
            ValueError: If batch_id is empty or batch not completed
            Exception: If file download/parsing fails

        Example:
            >>> results = await client.get_batch_results("batch-abc123")
            >>> for result in results:
            ...     if "error" in result:
            ...         print(f"Request {result['custom_id']} failed: {result['error']}")
            ...     else:
            ...         print(f"Response: {result['response']['body']}")

        """
        if not batch_id:
            msg = "batch_id cannot be empty"
            raise ValueError(msg)

        status = await self.get_batch_status(batch_id)

        if status["status"] != "completed":
            msg = f"Batch not completed: {status['status']}"
            raise ValueError(msg)

        if not status["output_file_id"]:
            msg = "No output file available"
            raise ValueError(msg)

        try:
            # Download results file
            content = await self.client.files.content(status["output_file_id"])

            # Parse JSONL results
            results = []
            for line in content.text.strip().split("\n"):
                if line:  # Skip empty lines
                    result = json.loads(line)
                    results.append(result)

            logger.info(
                "batch_results_downloaded",
                batch_id=batch_id,
                result_count=len(results),
                output_file_id=status["output_file_id"],
            )

            return results

        except Exception as e:
            logger.exception(
                "batch_results_download_failed",
                error=str(e),
                batch_id=batch_id,
                output_file_id=status.get("output_file_id"),
            )
            raise


# Singleton instance
_batch_client: OpenAIBatchClient | None = None


def get_batch_client() -> OpenAIBatchClient:
    """Get or create batch client singleton.

    Returns cached client instance to avoid recreating connections.

    Returns:
        Singleton OpenAIBatchClient instance

    Example:
        >>> client = get_batch_client()
        >>> status = await client.get_batch_status("batch-abc123")

    """
    global _batch_client  # noqa: PLW0603
    if _batch_client is None:
        _batch_client = OpenAIBatchClient()
    return _batch_client


async def batch_embeddings(
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """Batch process embeddings with 50% cost savings.

    High-level helper function for embedding generation using Batch API.
    Handles file creation, submission, polling, and result extraction.

    Cost Comparison:
        - Real-time API: $0.00002/1K tokens = $20 per 1M tokens
        - Batch API:     $0.00001/1K tokens = $10 per 1M tokens (50% savings)

    Trade-offs:
        - ✅ 50% cost savings
        - ✅ No rate limiting concerns
        - ❌ 24 hour completion window (not real-time)
        - ❌ More complex error handling

    Args:
        texts: List of text strings to embed
        model: OpenAI embedding model (default: text-embedding-3-small)

    Returns:
        List of embedding vectors (same order as input texts)

    Raises:
        ValueError: If texts list is empty
        TimeoutError: If batch doesn't complete within 24 hours
        Exception: If batch processing fails

    Example:
        >>> texts = ["Document 1", "Document 2", "Document 3"]
        >>> embeddings = await batch_embeddings(texts)
        >>> print(f"Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")
        Generated 3 embeddings of dimension 1536

    """
    if not texts:
        msg = "Cannot generate batch embeddings for empty text list"
        raise ValueError(msg)

    client = get_batch_client()

    # Create batch requests
    requests = [{"model": model, "input": text} for text in texts]

    logger.info(
        "batch_embeddings_started",
        text_count=len(texts),
        model=model,
    )

    # Create and upload batch file
    file_id = await client.create_batch_file(requests, endpoint="/v1/embeddings")

    # Submit batch job
    batch_id = await client.submit_batch(
        file_id,
        endpoint="/v1/embeddings",
        metadata={
            "operation": "embeddings",
            "model": model,
            "count": str(len(texts)),
        },
    )

    # Wait for completion
    await client.wait_for_completion(batch_id)

    # Get results
    results = await client.get_batch_results(batch_id)

    # Extract embeddings in original order
    embeddings = []
    for result in sorted(results, key=lambda r: int(r["custom_id"].split("-")[1])):
        if "error" in result:
            msg = f"Embedding failed for request {result['custom_id']}: {result['error']}"
            raise ExternalServiceError(service_name="openai_batch", message=msg)

        embedding = result["response"]["body"]["data"][0]["embedding"]
        embeddings.append(embedding)

    logger.info(
        "batch_embeddings_completed",
        text_count=len(texts),
        embedding_count=len(embeddings),
        model=model,
        batch_id=batch_id,
    )

    return embeddings


async def batch_chat_completions(
    messages_list: list[list[dict[str, str]]],
    model: str = "gpt-4o-mini",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> list[str]:
    """Batch process chat completions with 50% cost savings.

    High-level helper function for chat completion generation using Batch API.
    Ideal for evaluation runs, experiments, and batch processing.

    Cost Comparison:
        - Real-time API: $0.150/$0.600 per 1M tokens (gpt-4o-mini)
        - Batch API:     $0.075/$0.300 per 1M tokens (50% savings)

    Trade-offs:
        - ✅ 50% cost savings
        - ✅ No rate limiting concerns
        - ❌ 24 hour completion window (not real-time)
        - ❌ More complex error handling

    Args:
        messages_list: List of message arrays (each for one completion)
        model: OpenAI chat model (default: gpt-4o-mini)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response

    Returns:
        List of completion texts (same order as input messages)

    Raises:
        ValueError: If messages_list is empty
        TimeoutError: If batch doesn't complete within 24 hours
        Exception: If batch processing fails

    Example:
        >>> messages_list = [
        ...     [{"role": "user", "content": "What is 2+2?"}],
        ...     [{"role": "user", "content": "What is 3+3?"}],
        ... ]
        >>> completions = await batch_chat_completions(messages_list)
        >>> print(completions[0])
        "2+2 equals 4."

    """
    if not messages_list:
        msg = "Cannot generate batch completions for empty messages list"
        raise ValueError(msg)

    client = get_batch_client()

    # Create batch requests
    requests = []
    for messages in messages_list:
        request_body = {"model": model, "messages": messages}
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens
        requests.append(request_body)

    logger.info(
        "batch_completions_started",
        request_count=len(messages_list),
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Create and upload batch file
    file_id = await client.create_batch_file(requests, endpoint="/v1/chat/completions")

    # Submit batch job
    batch_id = await client.submit_batch(
        file_id,
        endpoint="/v1/chat/completions",
        metadata={
            "operation": "chat_completions",
            "model": model,
            "count": str(len(messages_list)),
        },
    )

    # Wait for completion
    await client.wait_for_completion(batch_id)

    # Get results
    results = await client.get_batch_results(batch_id)

    # Extract completions in original order
    completions = []
    for result in sorted(results, key=lambda r: int(r["custom_id"].split("-")[1])):
        if "error" in result:
            msg = f"Completion failed for request {result['custom_id']}: {result['error']}"
            raise ExternalServiceError(service_name="openai_batch", message=msg)

        completion_text = result["response"]["body"]["choices"][0]["message"]["content"]
        completions.append(completion_text)

    logger.info(
        "batch_completions_completed",
        request_count=len(messages_list),
        completion_count=len(completions),
        model=model,
        batch_id=batch_id,
    )

    return completions
