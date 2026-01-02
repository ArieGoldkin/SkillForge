---
name: pgvector-hybrid-rrf
description: Reciprocal Rank Fusion for hybrid search
version: 1.0.0
tags: [pgvector, hybrid, rrf, fusion, ranking]
size: atomic
domain: database
---

# Reciprocal Rank Fusion (RRF)

## The Problem

How do you combine vector scores (0.85) with BM25 scores (42.7)?

## The Solution

Use **rank** instead of score.

## Algorithm

```python
def rrf_score(rank: int, k: int = 60) -> float:
    """
    Calculate RRF score for a document at given rank.

    Args:
        rank: Position in result list (1-indexed)
        k: Smoothing constant (typically 60)

    Returns:
        Score between 0 and ~0.016 (1/k)
    """
    return 1.0 / (k + rank)

# Example:
# Document at rank 3 in vector search → 1/(60+3) = 0.0159
# Same document at rank 7 in BM25    → 1/(60+7) = 0.0149
# Combined RRF score = 0.0159 + 0.0149 = 0.0308
```

## Why It Works

- **Rank-based:** Ignores absolute scores (no normalization needed)
- **Symmetric:** Treats both searches equally
- **Robust:** Top results from either search get high scores

## SQL Implementation

```sql
WITH vector_results AS (
    SELECT id, row_number() OVER (ORDER BY embedding <=> $1) AS vrank
    FROM chunks
    WHERE embedding IS NOT NULL
    LIMIT 30
),
keyword_results AS (
    SELECT id, row_number() OVER (ORDER BY ts_rank_cd(content_tsvector, query) DESC) AS krank
    FROM chunks, plainto_tsquery('english', $2) query
    WHERE content_tsvector @@ query
    LIMIT 30
),
rrf AS (
    SELECT
        COALESCE(v.id, k.id) AS id,
        COALESCE(1.0 / (60 + v.vrank), 0) +
        COALESCE(1.0 / (60 + k.krank), 0) AS score
    FROM vector_results v
    FULL OUTER JOIN keyword_results k ON v.id = k.id
)
SELECT c.* FROM chunks c
JOIN rrf ON c.id = rrf.id
ORDER BY rrf.score DESC
LIMIT 10;
```

## SQLAlchemy Implementation

```python
K = 60  # RRF smoothing constant
FETCH_MULTIPLIER = 3  # Retrieve 3x for better coverage

async def hybrid_search(
    query: str,
    query_embedding: list[float],
    top_k: int = 10
) -> list[Chunk]:
    fetch_limit = top_k * FETCH_MULTIPLIER

    # Vector subquery with ranks
    vector_sq = (
        select(
            Chunk.id,
            func.row_number().over(
                order_by=Chunk.embedding.cosine_distance(query_embedding)
            ).label("vrank")
        )
        .where(Chunk.embedding.isnot(None))
        .limit(fetch_limit)
    ).subquery()

    # Keyword subquery with ranks
    ts_query = func.plainto_tsquery("english", query)
    keyword_sq = (
        select(
            Chunk.id,
            func.row_number().over(
                order_by=func.ts_rank_cd(Chunk.content_tsvector, ts_query).desc()
            ).label("krank")
        )
        .where(Chunk.content_tsvector.op("@@")(ts_query))
        .limit(fetch_limit)
    ).subquery()

    # RRF combination
    rrf_sq = (
        select(
            func.coalesce(vector_sq.c.id, keyword_sq.c.id).label("id"),
            (
                func.coalesce(1.0 / (K + vector_sq.c.vrank), 0) +
                func.coalesce(1.0 / (K + keyword_sq.c.krank), 0)
            ).label("score")
        )
        .select_from(
            vector_sq.outerjoin(keyword_sq, vector_sq.c.id == keyword_sq.c.id, full=True)
        )
        .order_by(literal("score").desc())
        .limit(top_k)
    ).subquery()

    # Fetch full chunks
    final = select(Chunk).join(rrf_sq, Chunk.id == rrf_sq.c.id)
    result = await session.execute(final)
    return result.scalars().all()
```

## Best Practices

- **Fetch multiplier:** Retrieve 3x results for better RRF coverage
- **k=60:** Standard smoothing constant, rarely needs tuning
- **Full outer join:** Include results from either search
