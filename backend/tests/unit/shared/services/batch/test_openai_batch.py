"""Tests for OpenAI Batch API client.

This module provides comprehensive tests for the OpenAI Batch API client,
covering:
- Batch file creation and upload
- Batch job submission with metadata
- Status polling and completion handling
- Result download and parsing
- Error handling and validation
- High-level helper functions (batch_embeddings)

Test Coverage:
- Happy path: Full batch workflow from creation to results
- Error cases: Invalid inputs, API failures, timeouts
- Edge cases: Empty requests, missing files, partial failures
- Integration: End-to-end batch processing simulation
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.services.batch.openai_batch import (
    OpenAIBatchClient,
    batch_embeddings,
    get_batch_client,
)


class TestOpenAIBatchClient:
    """Test suite for OpenAIBatchClient."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with API key."""
        with patch("app.shared.services.batch.openai_batch.settings") as mock:
            mock.OPENAI_API_KEY = "test-api-key"
            yield mock

    @pytest.fixture
    def mock_client(self, mock_settings):
        """Create OpenAIBatchClient with mocked AsyncOpenAI."""
        with patch("app.shared.services.batch.openai_batch.AsyncOpenAI") as mock_openai:
            client = OpenAIBatchClient()
            client.client = mock_openai.return_value
            yield client

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch("app.shared.services.batch.openai_batch.settings") as mock:
            mock.OPENAI_API_KEY = None

            with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
                OpenAIBatchClient()

    def test_init_success(self, mock_settings):
        """Test successful initialization."""
        with patch("app.shared.services.batch.openai_batch.AsyncOpenAI"):
            client = OpenAIBatchClient()

            assert client.batch_dir == Path("/tmp/skillforge_batches")
            assert client.batch_dir.exists()

    async def test_create_batch_file_empty_requests(self, mock_client):
        """Test create_batch_file raises error for empty requests."""
        with pytest.raises(ValueError, match="Cannot create batch file with empty requests"):
            await mock_client.create_batch_file([])

    async def test_create_batch_file_success(self, mock_client, tmp_path):
        """Test successful batch file creation and upload."""
        mock_client.batch_dir = tmp_path

        # Mock file upload response
        mock_client.client.files.create = AsyncMock(return_value=MagicMock(id="file-123"))

        requests = [
            {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]},
            {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "World"}]},
        ]

        file_id = await mock_client.create_batch_file(requests)

        assert file_id == "file-123"
        mock_client.client.files.create.assert_called_once()

        # Verify JSONL file was created
        jsonl_files = list(tmp_path.glob("batch_*.jsonl"))
        assert len(jsonl_files) == 1

        # Verify JSONL content
        with jsonl_files[0].open() as f:
            lines = f.readlines()
            assert len(lines) == 2
            import json

            line1 = json.loads(lines[0])
            assert line1["custom_id"] == "request-0"
            assert line1["method"] == "POST"
            assert line1["url"] == "/v1/chat/completions"
            assert line1["body"] == requests[0]

    async def test_create_batch_file_upload_failure(self, mock_client, tmp_path):
        """Test create_batch_file handles upload failures."""
        mock_client.batch_dir = tmp_path

        # Mock file upload failure
        mock_client.client.files.create = AsyncMock(side_effect=Exception("Upload failed"))

        requests = [{"model": "gpt-4o-mini", "messages": []}]

        with pytest.raises(Exception, match="Upload failed"):
            await mock_client.create_batch_file(requests)

    async def test_submit_batch_empty_file_id(self, mock_client):
        """Test submit_batch raises error for empty file_id."""
        with pytest.raises(ValueError, match="file_id cannot be empty"):
            await mock_client.submit_batch("")

    async def test_submit_batch_invalid_completion_window(self, mock_client):
        """Test submit_batch raises error for invalid completion window."""
        with pytest.raises(ValueError, match="Invalid completion_window"):
            await mock_client.submit_batch("file-123", completion_window="1h")

    async def test_submit_batch_success(self, mock_client):
        """Test successful batch submission."""
        mock_client.client.batches.create = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="validating",
            )
        )

        batch_id = await mock_client.submit_batch(
            "file-123",
            metadata={"dataset": "golden"},
        )

        assert batch_id == "batch-456"
        mock_client.client.batches.create.assert_called_once_with(
            input_file_id="file-123",
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"dataset": "golden"},
        )

    async def test_submit_batch_failure(self, mock_client):
        """Test submit_batch handles API failures."""
        mock_client.client.batches.create = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception, match="API error"):
            await mock_client.submit_batch("file-123")

    async def test_get_batch_status_empty_batch_id(self, mock_client):
        """Test get_batch_status raises error for empty batch_id."""
        with pytest.raises(ValueError, match="batch_id cannot be empty"):
            await mock_client.get_batch_status("")

    async def test_get_batch_status_success(self, mock_client):
        """Test successful batch status retrieval."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="completed",
                request_counts=MagicMock(total=10, completed=10, failed=0),
                output_file_id="output-789",
                error_file_id=None,
            )
        )

        status = await mock_client.get_batch_status("batch-456")

        assert status == {
            "id": "batch-456",
            "status": "completed",
            "request_counts": {
                "total": 10,
                "completed": 10,
                "failed": 0,
            },
            "output_file_id": "output-789",
            "error_file_id": None,
        }

    async def test_get_batch_status_failure(self, mock_client):
        """Test get_batch_status handles API failures."""
        mock_client.client.batches.retrieve = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception, match="API error"):
            await mock_client.get_batch_status("batch-456")

    async def test_wait_for_completion_empty_batch_id(self, mock_client):
        """Test wait_for_completion raises error for empty batch_id."""
        with pytest.raises(ValueError, match="batch_id cannot be empty"):
            await mock_client.wait_for_completion("")

    async def test_wait_for_completion_invalid_poll_interval(self, mock_client):
        """Test wait_for_completion raises error for invalid poll_interval."""
        with pytest.raises(ValueError, match="poll_interval must be positive"):
            await mock_client.wait_for_completion("batch-456", poll_interval=0)

        with pytest.raises(ValueError, match="poll_interval must be positive"):
            await mock_client.wait_for_completion("batch-456", poll_interval=-1)

    async def test_wait_for_completion_invalid_timeout(self, mock_client):
        """Test wait_for_completion raises error for invalid max_wait."""
        with pytest.raises(ValueError, match="max_wait must be positive"):
            await mock_client.wait_for_completion("batch-456", max_wait=0)

        with pytest.raises(ValueError, match="max_wait must be positive"):
            await mock_client.wait_for_completion("batch-456", max_wait=-1)

    async def test_wait_for_completion_success_immediate(self, mock_client):
        """Test wait_for_completion returns immediately if already completed."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="completed",
                request_counts=MagicMock(total=10, completed=10, failed=0),
                output_file_id="output-789",
                error_file_id=None,
            )
        )

        status = await mock_client.wait_for_completion(
            "batch-456",
            poll_interval=1,
            max_wait=5,
        )

        assert status["status"] == "completed"
        assert status["request_counts"]["completed"] == 10

    async def test_wait_for_completion_success_after_polling(self, mock_client):
        """Test wait_for_completion polls until completion."""
        # First call: in_progress, second call: completed
        mock_client.client.batches.retrieve = AsyncMock(
            side_effect=[
                MagicMock(
                    id="batch-456",
                    status="in_progress",
                    request_counts=MagicMock(total=10, completed=5, failed=0),
                    output_file_id=None,
                    error_file_id=None,
                ),
                MagicMock(
                    id="batch-456",
                    status="completed",
                    request_counts=MagicMock(total=10, completed=10, failed=0),
                    output_file_id="output-789",
                    error_file_id=None,
                ),
            ]
        )

        status = await mock_client.wait_for_completion(
            "batch-456",
            poll_interval=1,
            max_wait=5,
        )

        assert status["status"] == "completed"
        assert mock_client.client.batches.retrieve.call_count == 2

    async def test_wait_for_completion_timeout(self, mock_client):
        """Test wait_for_completion raises TimeoutError on max_wait."""
        # Always return in_progress
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="in_progress",
                request_counts=MagicMock(total=10, completed=5, failed=0),
                output_file_id=None,
                error_file_id=None,
            )
        )

        with pytest.raises(TimeoutError, match="did not complete within"):
            await mock_client.wait_for_completion(
                "batch-456",
                poll_interval=1,
                max_wait=2,  # Short timeout for fast test
            )

    async def test_wait_for_completion_failed_status(self, mock_client):
        """Test wait_for_completion returns failed status."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="failed",
                request_counts=MagicMock(total=10, completed=8, failed=2),
                output_file_id=None,
                error_file_id="error-999",
            )
        )

        status = await mock_client.wait_for_completion(
            "batch-456",
            poll_interval=1,
            max_wait=5,
        )

        assert status["status"] == "failed"
        assert status["request_counts"]["failed"] == 2

    async def test_get_batch_results_empty_batch_id(self, mock_client):
        """Test get_batch_results raises error for empty batch_id."""
        with pytest.raises(ValueError, match="batch_id cannot be empty"):
            await mock_client.get_batch_results("")

    async def test_get_batch_results_not_completed(self, mock_client):
        """Test get_batch_results raises error if batch not completed."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="in_progress",
                request_counts=MagicMock(total=10, completed=5, failed=0),
                output_file_id=None,
                error_file_id=None,
            )
        )

        with pytest.raises(ValueError, match="Batch not completed"):
            await mock_client.get_batch_results("batch-456")

    async def test_get_batch_results_no_output_file(self, mock_client):
        """Test get_batch_results raises error if no output file."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="completed",
                request_counts=MagicMock(total=10, completed=10, failed=0),
                output_file_id=None,  # No output file
                error_file_id=None,
            )
        )

        with pytest.raises(ValueError, match="No output file available"):
            await mock_client.get_batch_results("batch-456")

    async def test_get_batch_results_success(self, mock_client):
        """Test successful batch results download and parsing."""
        # Mock batch status
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="completed",
                request_counts=MagicMock(total=2, completed=2, failed=0),
                output_file_id="output-789",
                error_file_id=None,
            )
        )

        # Mock file content
        jsonl_content = """{"custom_id": "request-0", "response": {"body": {"choices": [{"message": {"content": "Hello"}}]}}}
{"custom_id": "request-1", "response": {"body": {"choices": [{"message": {"content": "World"}}]}}}"""

        mock_client.client.files.content = AsyncMock(return_value=MagicMock(text=jsonl_content))

        results = await mock_client.get_batch_results("batch-456")

        assert len(results) == 2
        assert results[0]["custom_id"] == "request-0"
        assert results[1]["custom_id"] == "request-1"

    async def test_get_batch_results_download_failure(self, mock_client):
        """Test get_batch_results handles download failures."""
        mock_client.client.batches.retrieve = AsyncMock(
            return_value=MagicMock(
                id="batch-456",
                status="completed",
                request_counts=MagicMock(total=10, completed=10, failed=0),
                output_file_id="output-789",
                error_file_id=None,
            )
        )

        mock_client.client.files.content = AsyncMock(side_effect=Exception("Download failed"))

        with pytest.raises(Exception, match="Download failed"):
            await mock_client.get_batch_results("batch-456")


class TestBatchClientSingleton:
    """Test suite for batch client singleton."""

    def test_get_batch_client_returns_singleton(self):
        """Test get_batch_client returns same instance."""
        with patch("app.shared.services.batch.openai_batch.settings") as mock:
            mock.OPENAI_API_KEY = "test-api-key"

            with patch("app.shared.services.batch.openai_batch.AsyncOpenAI"):
                # Clear singleton
                import app.shared.services.batch.openai_batch as batch_module

                batch_module._batch_client = None

                client1 = get_batch_client()
                client2 = get_batch_client()

                assert client1 is client2


class TestBatchEmbeddings:
    """Test suite for batch_embeddings helper function."""

    @pytest.fixture
    def mock_batch_client(self):
        """Mock batch client for testing."""
        with patch("app.shared.services.batch.openai_batch.get_batch_client") as mock:
            client = MagicMock()
            client.create_batch_file = AsyncMock(return_value="file-123")
            client.submit_batch = AsyncMock(return_value="batch-456")
            client.wait_for_completion = AsyncMock(return_value={"status": "completed"})
            client.get_batch_results = AsyncMock()
            mock.return_value = client
            yield client

    async def test_batch_embeddings_empty_texts(self):
        """Test batch_embeddings raises error for empty texts."""
        with pytest.raises(ValueError, match="Cannot generate batch embeddings"):
            await batch_embeddings([])

    async def test_batch_embeddings_success(self, mock_batch_client):
        """Test successful batch embeddings generation."""
        # Mock results
        mock_batch_client.get_batch_results.return_value = [
            {
                "custom_id": "request-0",
                "response": {"body": {"data": [{"embedding": [0.1, 0.2, 0.3]}]}},
            },
            {
                "custom_id": "request-1",
                "response": {"body": {"data": [{"embedding": [0.4, 0.5, 0.6]}]}},
            },
        ]

        texts = ["text1", "text2"]
        embeddings = await batch_embeddings(texts)

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]

        # Verify calls
        mock_batch_client.create_batch_file.assert_called_once()
        mock_batch_client.submit_batch.assert_called_once_with(
            "file-123",
            endpoint="/v1/embeddings",
            metadata={
                "operation": "embeddings",
                "model": "text-embedding-3-small",
                "count": "2",
            },
        )
        mock_batch_client.wait_for_completion.assert_called_once()

    async def test_batch_embeddings_custom_model(self, mock_batch_client):
        """Test batch_embeddings with custom model."""
        mock_batch_client.get_batch_results.return_value = [
            {
                "custom_id": "request-0",
                "response": {"body": {"data": [{"embedding": [0.1]}]}},
            },
        ]

        embeddings = await batch_embeddings(["text1"], model="text-embedding-3-large")

        # Verify model passed to create_batch_file
        call_args = mock_batch_client.create_batch_file.call_args
        requests = call_args[0][0]
        assert requests[0]["model"] == "text-embedding-3-large"

    async def test_batch_embeddings_with_error_result(self, mock_batch_client):
        """Test batch_embeddings raises error when result contains error."""
        mock_batch_client.get_batch_results.return_value = [
            {
                "custom_id": "request-0",
                "error": {"message": "API error"},
            },
        ]

        with pytest.raises(RuntimeError, match="Embedding failed"):
            await batch_embeddings(["text1"])

    async def test_batch_embeddings_preserves_order(self, mock_batch_client):
        """Test batch_embeddings preserves input order."""
        # Return results in reverse order
        mock_batch_client.get_batch_results.return_value = [
            {
                "custom_id": "request-2",
                "response": {"body": {"data": [{"embedding": [0.7, 0.8, 0.9]}]}},
            },
            {
                "custom_id": "request-1",
                "response": {"body": {"data": [{"embedding": [0.4, 0.5, 0.6]}]}},
            },
            {
                "custom_id": "request-0",
                "response": {"body": {"data": [{"embedding": [0.1, 0.2, 0.3]}]}},
            },
        ]

        texts = ["text1", "text2", "text3"]
        embeddings = await batch_embeddings(texts)

        # Should be sorted by request ID, not result order
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        assert embeddings[2] == [0.7, 0.8, 0.9]
