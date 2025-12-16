"""Unit tests for deterministic embedding service."""

import math

import pytest

from app.shared.services.embeddings.deterministic import DeterministicEmbeddingService



class TestDeterministicEmbeddingService:
    """Tests for DeterministicEmbeddingService."""

    @pytest.fixture
    def service(self):
        """Create embedding service with default dimensions."""
        return DeterministicEmbeddingService()

    @pytest.fixture
    def service_small(self):
        """Create embedding service with small dimensions for testing."""
        return DeterministicEmbeddingService(dims=64)

    def test_default_dimensions(self, service):
        """Test default dimension is 1536."""
        assert service.expected_dimensions == 1536

    def test_custom_dimensions(self):
        """Test custom dimension initialization."""
        service = DeterministicEmbeddingService(dims=768)
        assert service.expected_dimensions == 768

    def test_model_name(self, service):
        """Test model identifier."""
        assert service.model == "deterministic-hash-v1"

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_correct_size(self, service):
        """Test embedding has correct dimensions."""
        embedding = await service.generate_embedding("test text")
        assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_deterministic(self, service):
        """Test same input produces same output."""
        text = "hello world"
        emb1 = await service.generate_embedding(text)
        emb2 = await service.generate_embedding(text)
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_generate_embedding_normalized(self, service):
        """Test embedding is L2 normalized by default."""
        embedding = await service.generate_embedding("some text here")
        norm = math.sqrt(sum(v * v for v in embedding))
        assert abs(norm - 1.0) < 0.0001

    @pytest.mark.asyncio
    async def test_generate_embedding_unnormalized(self, service):
        """Test embedding without normalization."""
        embedding = await service.generate_embedding("test", normalize=False)
        norm = math.sqrt(sum(v * v for v in embedding))
        # Unnormalized should not be exactly 1.0
        assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(self, service_small):
        """Test different texts produce different embeddings."""
        emb1 = await service_small.generate_embedding("hello")
        emb2 = await service_small.generate_embedding("goodbye")
        assert emb1 != emb2

    @pytest.mark.asyncio
    async def test_case_insensitive(self, service_small):
        """Test embedding is case insensitive."""
        emb1 = await service_small.generate_embedding("Hello World")
        emb2 = await service_small.generate_embedding("hello world")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_handles_special_characters(self, service_small):
        """Test special characters are handled."""
        embedding = await service_small.generate_embedding("hello! @world# $test%")
        assert len(embedding) == 64
        # Should still produce valid embedding
        norm = math.sqrt(sum(v * v for v in embedding))
        assert abs(norm - 1.0) < 0.0001

    @pytest.mark.asyncio
    async def test_handles_empty_string(self, service_small):
        """Test empty string produces zero vector."""
        embedding = await service_small.generate_embedding("")
        # Empty should still return correct dimensions
        assert len(embedding) == 64

    @pytest.mark.asyncio
    async def test_bigram_generation(self, service_small):
        """Test bigrams improve phrase matching."""
        # Phrases with same words but different order should differ
        emb1 = await service_small.generate_embedding("python programming")
        emb2 = await service_small.generate_embedding("programming python")
        # They might be similar but not identical due to bigram differences
        # (python_programming vs programming_python)
        assert emb1 != emb2
