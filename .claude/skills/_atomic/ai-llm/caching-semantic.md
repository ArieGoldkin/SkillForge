---
name: caching-semantic
description: Redis semantic cache implementation with vector similarity
version: 1.0.0
tags: [llm, caching, redis, vectors]
size: atomic
domain: ai-llm
---

# Redis Semantic Cache

## Schema Design

```python
CACHE_INDEX_SCHEMA = {
    "index": {
        "name": "llm_semantic_cache",
        "prefix": "cache:",
    },
    "fields": [
        {"name": "agent_type", "type": "tag"},
        {"name": "content_type", "type": "tag"},
        {"name": "input_hash", "type": "tag"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": 1536,
                "distance_metric": "cosine",
                "algorithm": "hnsw",
            }
        },
        {"name": "response", "type": "text"},
        {"name": "created_at", "type": "numeric"},
        {"name": "hit_count", "type": "numeric"},
        {"name": "quality_score", "type": "numeric"},
    ]
}
```

## Service Implementation

```python
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redis import Redis

class SemanticCacheService:
    def __init__(self, redis_url: str, threshold: float = 0.92):
        self.client = Redis.from_url(redis_url)
        self.threshold = threshold
        self.embedding_service = EmbeddingService()
        self.index = SearchIndex.from_dict(CACHE_INDEX_SCHEMA, self.client)
        self.index.create(overwrite=False)

    async def get(
        self,
        content: str,
        agent_type: str,
        content_type: str | None = None
    ) -> CacheEntry | None:
        embedding = await self.embedding_service.embed_text(content[:2000])

        filter_expr = f"@agent_type:{{{agent_type}}}"
        if content_type:
            filter_expr += f" @content_type:{{{content_type}}}"

        query = VectorQuery(
            vector=embedding,
            vector_field_name="embedding",
            return_fields=["response", "quality_score", "hit_count"],
            num_results=1,
            filter_expression=filter_expr
        )

        results = self.index.query(query)

        if results and len(results) > 0:
            result = results[0]
            distance = float(result.get("vector_distance", 1.0))

            if distance <= (1 - self.threshold):
                self.client.hincrby(result["id"], "hit_count", 1)
                return CacheEntry(
                    response=json.loads(result["response"]),
                    quality_score=float(result["quality_score"]),
                    distance=distance
                )

        return None

    async def set(
        self,
        content: str,
        response: dict,
        agent_type: str,
        quality_score: float = 1.0
    ) -> None:
        content_preview = content[:2000]
        embedding = await self.embedding_service.embed_text(content_preview)

        key = f"cache:{agent_type}:{hash_content(content_preview)}"

        data = {
            "agent_type": agent_type,
            "input_hash": hash_content(content_preview),
            "embedding": embedding,
            "response": json.dumps(response),
            "created_at": time.time(),
            "hit_count": 0,
            "quality_score": quality_score,
        }

        self.client.hset(key, mapping=data)
        self.client.expire(key, ttl=86400)  # 24 hours
```

## Cache Warming

```python
async def warm_cache_from_golden_dataset(
    cache: SemanticCache,
    min_quality: float = 0.8
) -> int:
    analyses = await db.query(
        "SELECT * FROM analyses WHERE confidence_score >= ?",
        (min_quality,)
    )

    warmed = 0
    for analysis in analyses:
        for finding in analysis.findings:
            await cache.set(
                content=analysis.content,
                response=finding.output,
                agent_type=finding.agent_type,
                quality_score=finding.confidence_score
            )
            warmed += 1

    return warmed
```

## Metadata Filtering

```python
# Filter by agent_type + content_type
query = VectorQuery(
    vector=embedding,
    filter_expression="@agent_type:{security_auditor} @content_type:{article}"
)

# Add difficulty level
query = VectorQuery(
    vector=embedding,
    filter_expression="""
        @agent_type:{security_auditor}
        @content_type:{article}
        @difficulty_level:{advanced}
    """
)
```

## Docker Setup

```yaml
services:
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
      - "8001:8001"  # RedisInsight UI
    volumes:
      - redis_data:/data
```
