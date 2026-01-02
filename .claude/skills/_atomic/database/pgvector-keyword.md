---
name: pgvector-keyword
description: Full-text search with PostgreSQL BM25
version: 1.0.0
tags: [postgres, full-text, bm25, keyword, tsvector]
size: atomic
domain: database
---

# PostgreSQL Full-Text Search (BM25)

## How It Works

1. Tokenize query: `"database indexing"` → `database & indexing`
2. Full-text search: `WHERE content_tsvector @@ to_tsquery('database & indexing')`
3. Rank by BM25 score (TF-IDF + document length normalization)

## Schema

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,

    -- Pre-computed tsvector (MUCH faster than to_tsvector on query)
    content_tsvector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', content)
    ) STORED
);

-- GIN index for full-text search
CREATE INDEX idx_chunks_content_tsvector ON chunks
    USING gin (content_tsvector);
```

## Basic Query

```sql
-- Find matching chunks with BM25 ranking
SELECT id, content, ts_rank_cd(content_tsvector, query) AS score
FROM chunks, plainto_tsquery('english', 'database indexing') query
WHERE content_tsvector @@ query
ORDER BY score DESC
LIMIT 10;
```

## Query Types

```sql
-- plainto_tsquery: Simple words with AND
plainto_tsquery('database indexing')  -- database & indexing

-- phraseto_tsquery: Exact phrase
phraseto_tsquery('database indexing')  -- database <-> indexing

-- to_tsquery: Full control
to_tsquery('database | indexing')  -- database OR indexing
to_tsquery('!database')            -- NOT database
```

## SQLAlchemy Implementation

```python
from sqlalchemy import func, select

async def keyword_search(
    query: str,
    top_k: int = 10
) -> list[Chunk]:
    """Full-text search with BM25 ranking."""

    ts_query = func.plainto_tsquery("english", query)

    stmt = (
        select(
            Chunk,
            func.ts_rank_cd(Chunk.content_tsvector, ts_query).label("score")
        )
        .where(Chunk.content_tsvector.op("@@")(ts_query))
        .order_by(func.ts_rank_cd(Chunk.content_tsvector, ts_query).desc())
        .limit(top_k)
    )

    result = await session.execute(stmt)
    return [row.Chunk for row in result]
```

## Performance: Pre-computed vs On-the-fly

```sql
-- SLOW: Computes tsvector on every query
WHERE to_tsvector('english', content) @@ to_tsquery('database')

-- FAST: Uses pre-computed column with GIN index
WHERE content_tsvector @@ to_tsquery('database')
```

**Speedup:** 5-10x faster with pre-computed `tsvector`

## Ranking Functions

```sql
-- ts_rank: Standard ranking
ts_rank(content_tsvector, query)

-- ts_rank_cd: Cover density ranking (better for long docs)
ts_rank_cd(content_tsvector, query)
```

## Strengths & Weaknesses

**Strengths:**
- Fast exact matches
- Handles technical terms well
- Works for rare/specific phrases

**Weaknesses:**
- No semantic understanding
- Requires exact word matches
- Sensitive to typos
