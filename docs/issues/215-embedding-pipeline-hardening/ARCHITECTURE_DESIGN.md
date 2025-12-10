# Issue #215: Backend Embedding Pipeline Hardening

## Architecture Design Document

**Status**: Design Phase
**Sprint**: 8
**Author**: Claude Code
**Created**: 2025-12-10

---

## 1. Executive Summary

This document outlines the architecture for hardening the embedding pipeline with:
- **Token-aware chunking** with semantic break preference
- **Batch embedding** via OpenAI's multi-input API
- **Hash-based deduplication** to skip unchanged text
- **Enhanced per-chunk metadata** for observability
- **Database schema improvements** with proper indexing

---

## 2. Current State Analysis

### 2.1 Existing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CURRENT EMBEDDING PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  extract_content_node                                                    │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  chunk_content   │───▶│ generate_embed-  │───▶│ store_embeddings │  │
│  │                  │    │ dings_batch      │    │                  │  │
│  │  • Coarse chunks │    │                  │    │  • Bulk insert   │  │
│  │  • Fine chunks   │    │  ❌ Sequential   │    │  • FK handling   │  │
│  │  • Dedup (SHA256)│    │     API calls    │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current Limitations

| Area | Current State | Gap |
|------|--------------|-----|
| **Chunking** | Token-aware windows (900/600) | No token count stored per chunk |
| **Batching** | Sequential API calls | OpenAI supports 100+ per batch |
| **Dedup** | SHA256 hash computed | Hash not indexed, no cross-analysis dedup |
| **Metadata** | Basic (path, granularity) | Missing token_count, truncation flag |
| **Indexes** | analysis_id, granularity | Missing hash index, HNSW vector index |

### 2.3 Key Files

| File | Purpose |
|------|---------|
| `app/services/embeddings.py` | Embedding generation (8K token limit) |
| `app/services/chunking/chunker.py` | Two-level chunking (coarse/fine) |
| `app/services/chunking/dedup.py` | SHA256 deduplication |
| `app/models/analysis_chunk.py` | Database model |
| `app/workflows/tasks/generate_embedding.py` | Workflow task |
| `app/workflows/tasks/store_embeddings.py` | Storage task |

---

## 3. Proposed Architecture

### 3.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      HARDENED EMBEDDING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  extract_content_node                                                    │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────┐                                                    │
│  │  chunk_content   │                                                    │
│  │                  │                                                    │
│  │  • Token budgets │                                                    │
│  │  • Semantic breaks│                                                   │
│  │  • Token metadata │                                                   │
│  └────────┬─────────┘                                                    │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                           │
│  │   hash_dedup     │───▶│  Check existing  │                           │
│  │                  │    │  hashes in DB    │                           │
│  │  • SHA256 hash   │    │                  │                           │
│  │  • Model+version │    │  Skip if exists  │                           │
│  └────────┬─────────┘    └──────────────────┘                           │
│           │                                                              │
│           ▼ (new chunks only)                                            │
│  ┌──────────────────┐                                                    │
│  │  batch_embed     │                                                    │
│  │                  │                                                    │
│  │  ✅ Batch API    │                                                   │
│  │  • 50-100/batch  │                                                    │
│  │  • Adaptive size │                                                    │
│  └────────┬─────────┘                                                    │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                    │
│  │ store_embeddings │                                                    │
│  │                  │                                                    │
│  │  • Enhanced meta │                                                    │
│  │  • Bulk upsert   │                                                    │
│  │  • HNSW indexed  │                                                    │
│  └──────────────────┘                                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Design

#### 3.2.1 Token-Aware Chunking Enhancement

**Current**: Chunks may exceed token limits, causing truncation at embedding time.

**Proposed**: Pre-validate token budgets during chunking.

```python
@dataclass
class ChunkText:
    text: str
    path: list[str]
    section_title: str | None
    granularity: Literal["coarse", "fine", "summary"]
    chunk_idx: int
    chunk_total: int
    # NEW FIELDS
    token_count: int          # Actual token count
    was_truncated: bool       # True if chunk was trimmed
    content_hash: str         # SHA256 for dedup
```

**Chunking Strategy**:
1. Prefer semantic breaks (paragraph, heading boundaries)
2. Hard limit at 7,500 tokens (below 8K API limit)
3. Track token count per chunk
4. Store truncation flag if content was trimmed

#### 3.2.2 Batch Embedding Service

**Current**: Sequential API calls (1 embedding per request).

**Proposed**: Batch multiple texts per API call.

```python
class BatchEmbeddingService:
    """Batch embedding with adaptive sizing."""

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 50
    ) -> list[EmbeddingVector]:
        """
        Embed multiple texts in single API call.

        OpenAI supports up to 2048 texts per batch,
        but we limit to 50-100 for latency control.
        """
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch  # Multi-input!
            )
            results.extend([r.embedding for r in response.data])
        return results
```

**Batch Size Strategy**:
- Default: 50 texts per batch
- Adaptive: Reduce on 429/5xx errors (use existing backpressure)
- Max: 100 texts per batch
- Cooldown: 30s before size increase

#### 3.2.3 Hash-Based Deduplication

**Current**: Hash computed but not used for skip logic.

**Proposed**: Check database for existing hashes before embedding.

```python
async def deduplicate_chunks(
    chunks: list[ChunkText],
    analysis_id: UUID,
    repo: ChunkRepository
) -> tuple[list[ChunkText], DedupStats]:
    """
    Skip chunks that already exist in database.

    Hash = SHA256(normalized_text + model + model_version)
    """
    # Compute hashes for all chunks
    hashes = [compute_chunk_hash(c) for c in chunks]

    # Query existing hashes in single DB call
    existing = await repo.get_existing_hashes(
        analysis_id=analysis_id,
        hashes=hashes
    )

    # Filter out already-embedded chunks
    new_chunks = [c for c, h in zip(chunks, hashes) if h not in existing]

    return new_chunks, DedupStats(
        total=len(chunks),
        skipped=len(existing),
        to_embed=len(new_chunks)
    )
```

**Hash Composition**:
```python
def compute_chunk_hash(chunk: ChunkText, model: str, version: str) -> str:
    """
    Hash includes model info to re-embed when model changes.
    """
    content = f"{chunk.text.strip().lower()}|{model}|{version}"
    return hashlib.sha256(content.encode()).hexdigest()
```

---

## 4. Database Schema

### 4.1 Enhanced analysis_chunks Table

```sql
-- Current columns (keep as-is)
id              UUID PRIMARY KEY
analysis_id     UUID REFERENCES analyses(id)
vector          VECTOR(1536)
granularity     VARCHAR(20)
path            JSONB
section_title   TEXT
chunk_idx       INTEGER
chunk_total     INTEGER
hash            VARCHAR(128)
model           VARCHAR(100)
model_version   VARCHAR(50)
snippet         TEXT
content_type    VARCHAR(50)
language        VARCHAR(20)
created_at      TIMESTAMP
updated_at      TIMESTAMP

-- NEW COLUMNS
token_count     INTEGER         -- Tokens in this chunk
was_truncated   BOOLEAN         -- True if truncated
embedding_ms    INTEGER         -- Embedding latency (ms)
```

### 4.2 Index Strategy

```sql
-- Existing indexes (keep)
CREATE INDEX ix_analysis_chunks_analysis_id ON analysis_chunks(analysis_id);
CREATE INDEX ix_analysis_chunks_granularity ON analysis_chunks(granularity);

-- NEW indexes for hardening
CREATE INDEX ix_analysis_chunks_hash ON analysis_chunks(hash);
CREATE INDEX ix_analysis_chunks_content_type ON analysis_chunks(content_type);
CREATE INDEX ix_analysis_chunks_created_at ON analysis_chunks(created_at);

-- Compound index for dedup lookups
CREATE INDEX ix_analysis_chunks_dedup
    ON analysis_chunks(analysis_id, hash);

-- HNSW vector index for similarity search
CREATE INDEX ix_analysis_chunks_vector_hnsw
    ON analysis_chunks
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### 4.3 Migration Plan

**Migration 1**: Add new columns (backward compatible)
```sql
ALTER TABLE analysis_chunks ADD COLUMN token_count INTEGER;
ALTER TABLE analysis_chunks ADD COLUMN was_truncated BOOLEAN DEFAULT FALSE;
ALTER TABLE analysis_chunks ADD COLUMN embedding_ms INTEGER;
```

**Migration 2**: Add new indexes (can be concurrent)
```sql
CREATE INDEX CONCURRENTLY ix_analysis_chunks_hash ON analysis_chunks(hash);
CREATE INDEX CONCURRENTLY ix_analysis_chunks_content_type ON analysis_chunks(content_type);
CREATE INDEX CONCURRENTLY ix_analysis_chunks_created_at ON analysis_chunks(created_at);
CREATE INDEX CONCURRENTLY ix_analysis_chunks_dedup ON analysis_chunks(analysis_id, hash);
```

**Migration 3**: Add HNSW vector index
```sql
CREATE INDEX CONCURRENTLY ix_analysis_chunks_vector_hnsw
    ON analysis_chunks
    USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

## 5. Configuration

### 5.1 New Settings

```python
# app/core/config.py additions

# Chunking
CHUNK_MAX_TOKENS: int = 7500          # Hard limit per chunk
CHUNK_PREFER_SEMANTIC_BREAKS: bool = True

# Batch Embedding
EMBEDDING_BATCH_SIZE: int = 50        # Texts per API call
EMBEDDING_BATCH_MAX: int = 100        # Maximum batch size
EMBEDDING_BATCH_MIN: int = 10         # Minimum batch size

# Deduplication
DEDUP_CHECK_DATABASE: bool = True     # Check existing hashes
DEDUP_HASH_INCLUDES_MODEL: bool = True # Include model in hash

# Telemetry
TELEMETRY_LOG_BATCH_STATS: bool = True
TELEMETRY_LOG_DEDUP_STATS: bool = True
```

---

## 6. Telemetry & Metrics

### 6.1 New Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `embedding_batch_size` | Histogram | model | Texts per batch |
| `embedding_batch_latency_ms` | Histogram | model | Batch duration |
| `dedup_skip_count` | Counter | analysis_id | Skipped chunks |
| `dedup_embed_count` | Counter | analysis_id | New embeddings |
| `chunk_token_count` | Histogram | granularity | Tokens per chunk |
| `chunk_truncation_count` | Counter | granularity | Truncated chunks |

### 6.2 Logging (No Raw Text)

```python
logger.info(
    "batch_embedding_complete",
    batch_size=len(batch),
    latency_ms=latency,
    tokens_total=sum(c.token_count for c in batch),
    dedup_skipped=stats.skipped,
    # NO raw text logged
)
```

---

## 7. Implementation Plan

### Phase 1: Schema & Infrastructure (Day 1)
- [ ] Add new columns to analysis_chunks model
- [ ] Create Alembic migration for columns
- [ ] Create Alembic migration for indexes
- [ ] Add configuration settings

### Phase 2: Chunking Enhancement (Day 1-2)
- [ ] Add token_count field to ChunkText dataclass
- [ ] Add was_truncated field to ChunkText dataclass
- [ ] Implement token budget validation in chunker
- [ ] Update chunk_content task to populate new fields

### Phase 3: Batch Embedding (Day 2)
- [ ] Create BatchEmbeddingService class
- [ ] Implement multi-input API calls
- [ ] Integrate with existing backpressure system
- [ ] Update generate_embeddings_batch to use batching

### Phase 4: Hash Deduplication (Day 2-3)
- [ ] Implement compute_chunk_hash with model info
- [ ] Add get_existing_hashes to ChunkRepository
- [ ] Create deduplicate_chunks function
- [ ] Wire into workflow before embedding

### Phase 5: Storage & Telemetry (Day 3)
- [ ] Update store_embeddings to persist new fields
- [ ] Add batch/dedup metrics to MetricsService
- [ ] Update logging (no raw text)
- [ ] Write unit tests

### Phase 6: Testing & Documentation (Day 3-4)
- [ ] Unit tests for all new components
- [ ] Integration test for full pipeline
- [ ] Update design documentation
- [ ] Performance benchmarks

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# test_batch_embedding.py
async def test_batch_embedding_groups_texts():
    """Verify texts are batched correctly."""

async def test_batch_embedding_respects_max_size():
    """Verify batch size limits are enforced."""

async def test_batch_embedding_handles_rate_limit():
    """Verify backpressure reduces batch size on 429."""

# test_hash_dedup.py
def test_hash_includes_model_version():
    """Different models produce different hashes."""

async def test_dedup_skips_existing_chunks():
    """Chunks with existing hashes are skipped."""

async def test_dedup_processes_new_chunks():
    """New chunks are sent for embedding."""

# test_chunking_tokens.py
def test_chunk_respects_token_limit():
    """Chunks don't exceed CHUNK_MAX_TOKENS."""

def test_chunk_tracks_token_count():
    """Each chunk has accurate token_count."""

def test_chunk_prefers_semantic_breaks():
    """Chunker breaks at paragraphs when possible."""
```

### 8.2 Integration Tests

```python
async def test_full_pipeline_with_dedup():
    """End-to-end: chunk → dedup → batch embed → store."""

async def test_reprocessing_skips_unchanged():
    """Re-running same content skips embedding."""
```

---

## 9. Rollback Plan

If issues arise:

1. **Disable dedup check**: Set `DEDUP_CHECK_DATABASE=False`
2. **Reduce batch size**: Set `EMBEDDING_BATCH_SIZE=1` (sequential)
3. **Revert migration**: Drop new columns/indexes if needed

---

## 10. Success Criteria

| Metric | Target |
|--------|--------|
| Batch API utilization | >90% of embeddings via batch |
| Dedup hit rate | >50% on re-analysis |
| Truncation rate | <1% of chunks |
| Token metadata coverage | 100% of chunks have token_count |
| Index usage | Hash lookups use index |

---

## Appendix A: OpenAI Batch Embedding API

```python
# Single input (current)
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Single text"
)

# Multi-input (proposed)
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["Text 1", "Text 2", "Text 3", ...]  # Up to 2048
)

# Response contains embeddings in same order as input
for i, embedding in enumerate(response.data):
    vectors[i] = embedding.embedding
```

---

## Appendix B: HNSW Index Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `m` | 16 | Connections per node (balance speed/recall) |
| `ef_construction` | 64 | Build-time accuracy (higher = slower build, better recall) |
| `vector_cosine_ops` | - | Cosine distance for normalized vectors |

Query-time `ef_search` can be tuned per query for speed/accuracy tradeoff.
