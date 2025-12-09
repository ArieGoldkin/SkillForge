import asyncio
from uuid import uuid4

import pytest

from app.workflows.tasks.store_embeddings import store_embeddings


class FakeChunkRepo:
    def __init__(self) -> None:
        self.items: list[dict] = []

    async def create_many(self, items):
        self.items.extend(items)


@pytest.mark.asyncio
async def test_store_embeddings_persists_payloads():
    repo = FakeChunkRepo()
    analysis_id = uuid4()
    payloads = [
        (
            [0.1, 0.2],
            {
                "granularity": "fine",
                "path": ["Intro"],
                "chunk_idx": 0,
                "chunk_total": 1,
                "hash": "abc",
                "model": "text-embedding-3-small",
                "model_version": "1",
                "snippet": "hello",
            },
        )
    ]

    stored = await store_embeddings(payloads, analysis_id, repo)

    assert len(stored) == 1
    assert len(repo.items) == 1
    assert repo.items[0]["analysis_id"] == analysis_id
    assert repo.items[0]["granularity"] == "fine"
    assert repo.items[0]["path"] == ["Intro"]

