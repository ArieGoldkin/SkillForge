"""Unit tests for OpenAI Batch API integration.

Tests the integration points between EmbeddingService and batch API,
configuration-driven behavior, and automatic fallback logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.shared.services.embeddings.service import EmbeddingService


class TestBatchAPIIntegration:
    """Test Batch API integration with EmbeddingService."""

    @pytest.mark.asyncio
    async def test_batch_api_disabled_by_default(self):
        """Verify Batch API is disabled by default in config."""
        assert settings.OPENAI_BATCH_ENABLED is False
        assert settings.OPENAI_BATCH_COMPLETION_WINDOW == "24h"
        assert settings.OPENAI_BATCH_MIN_SIZE == 10

    @pytest.mark.asyncio
    async def test_embeddings_batch_respects_config_disabled(self):
        """When OPENAI_BATCH_ENABLED=false, use real-time API."""
        with patch.object(settings, "OPENAI_BATCH_ENABLED", new=False):
            service = EmbeddingService()

            # Mock the real-time batch method
            with patch.object(service, "_embed_batch", new_callable=AsyncMock) as mock_embed_batch:
                mock_embed_batch.return_value = [
                    ([0.1] * 1536, 100.0),
                    ([0.2] * 1536, 100.0),
                ]

                texts = ["text1", "text2"]
                results = await service.generate_embeddings_batch(texts)

                # Should use real-time API
                assert len(results) == 2
                mock_embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_embeddings_batch_uses_batch_api_when_enabled(self):
        """When OPENAI_BATCH_ENABLED=true and batch size >= min, use Batch API."""
        with patch.object(settings, "OPENAI_BATCH_ENABLED", new=True):
            with patch.object(settings, "OPENAI_BATCH_MIN_SIZE", new=2):
                service = EmbeddingService()

                # Mock the Batch API method
                with patch.object(
                    service,
                    "_generate_embeddings_batch_api",
                    new_callable=AsyncMock,
                ) as mock_batch_api:
                    mock_batch_api.return_value = [
                        ([0.1] * 1536, 1000.0),
                        ([0.2] * 1536, 1000.0),
                    ]

                    texts = ["text1", "text2"]
                    results = await service.generate_embeddings_batch(texts)

                    # Should use Batch API
                    assert len(results) == 2
                    mock_batch_api.assert_called_once_with(texts, True)

    @pytest.mark.asyncio
    async def test_embeddings_batch_explicit_override(self):
        """use_batch_api parameter overrides config."""
        with patch.object(settings, "OPENAI_BATCH_ENABLED", new=False):
            service = EmbeddingService()

            # Mock the Batch API method
            with patch.object(
                service,
                "_generate_embeddings_batch_api",
                new_callable=AsyncMock,
            ) as mock_batch_api:
                mock_batch_api.return_value = [([0.1] * 1536, 1000.0)]

                texts = ["text1"]
                # Explicitly enable Batch API despite config
                results = await service.generate_embeddings_batch(texts, use_batch_api=True)

                # Should use Batch API
                assert len(results) == 1
                mock_batch_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_api_fallback_on_error(self):
        """Batch API errors should fall back to real-time API."""
        service = EmbeddingService()

        # Mock batch_embeddings from the batch module to fail
        with patch(
            "app.shared.services.batch.openai_batch.batch_embeddings",
            new_callable=AsyncMock,
        ) as mock_batch_embeddings:
            mock_batch_embeddings.side_effect = RuntimeError("Batch API failed")

            # Mock real-time API to succeed
            with patch.object(service, "_embed_batch", new_callable=AsyncMock) as mock_embed_batch:
                mock_embed_batch.return_value = [([0.1] * 1536, 100.0)]

                texts = ["text1"]
                # Force Batch API usage (should fail and fall back)
                results = await service.generate_embeddings_batch(texts, use_batch_api=True)

                # Should fall back to real-time API
                assert len(results) == 1
                mock_batch_embeddings.assert_called_once()
                mock_embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_size_threshold(self):
        """Batch API only used when batch size >= OPENAI_BATCH_MIN_SIZE."""
        with patch.object(settings, "OPENAI_BATCH_ENABLED", new=True):
            with patch.object(settings, "OPENAI_BATCH_MIN_SIZE", new=10):
                service = EmbeddingService()

                # Mock the real-time batch method
                with patch.object(
                    service, "_embed_batch", new_callable=AsyncMock
                ) as mock_embed_batch:
                    mock_embed_batch.return_value = [([0.1] * 1536, 100.0)]

                    # Small batch (below threshold)
                    texts = ["text1", "text2"]  # Only 2 texts, threshold is 10
                    results = await service.generate_embeddings_batch(texts)

                    # Should use real-time API
                    assert len(results) == 1
                    mock_embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_completions_import(self):
        """Verify batch_chat_completions can be imported."""
        from app.shared.services.batch.openai_batch import batch_chat_completions

        # Verify function exists and has correct signature
        assert callable(batch_chat_completions)
        assert batch_chat_completions.__name__ == "batch_chat_completions"
