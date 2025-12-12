"""External sanity test: verify OpenAI embeddings connectivity.

This suite is intentionally tiny to cap CI cost while still verifying
real external integration works end-to-end.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.external
@pytest.mark.asyncio
async def test_openai_embedding_service_returns_expected_dimensions() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    # Ensure settings cache picks up env var (EmbeddingService reads module-level settings)
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.core.config

    app.core.config.settings = get_settings()

    from app.services.embeddings import EmbeddingService

    service = EmbeddingService()
    embedding = await service.generate_embedding("ci-sanity", normalize=True)

    assert isinstance(embedding, list)
    assert len(embedding) == 1536


