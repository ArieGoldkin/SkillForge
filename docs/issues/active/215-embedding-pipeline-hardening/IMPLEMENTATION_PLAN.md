# Issue #215: Implementation Plan

## Task Breakdown

### Phase 1: Schema & Infrastructure

#### Task 1.1: Update AnalysisChunk Model
**File**: `app/models/analysis_chunk.py`
```python
# Add columns:
token_count = Column(Integer, nullable=True)
was_truncated = Column(Boolean, default=False)
embedding_ms = Column(Integer, nullable=True)
```

#### Task 1.2: Create Alembic Migration
**File**: `alembic/versions/YYYYMMDD_add_chunk_metadata.py`
- Add `token_count`, `was_truncated`, `embedding_ms` columns
- Add indexes: `hash`, `content_type`, `created_at`
- Add compound index: `(analysis_id, hash)`
- Add HNSW vector index

#### Task 1.3: Add Configuration
**File**: `app/core/config.py`
```python
CHUNK_MAX_TOKENS: int = 7500
EMBEDDING_BATCH_SIZE: int = 50
EMBEDDING_BATCH_MAX: int = 100
DEDUP_CHECK_DATABASE: bool = True
```

---

### Phase 2: Chunking Enhancement

#### Task 2.1: Enhance ChunkText Dataclass
**File**: `app/services/chunking/types.py`
```python
@dataclass
class ChunkText:
    text: str
    path: list[str]
    section_title: str | None
    granularity: Literal["coarse", "fine", "summary"]
    chunk_idx: int
    chunk_total: int
    token_count: int          # NEW
    was_truncated: bool       # NEW
    content_hash: str         # NEW
```

#### Task 2.2: Update Chunker with Token Validation
**File**: `app/services/chunking/chunker.py`
- Add token counting during chunk creation
- Enforce max token limit (7500)
- Prefer semantic breaks (paragraphs, headings)
- Track truncation

#### Task 2.3: Update chunk_content Task
**File**: `app/workflows/tasks/chunk_content.py`
- Populate new fields in ChunkText
- Compute content hash at chunking time

---

### Phase 3: Batch Embedding

#### Task 3.1: Create BatchEmbeddingService
**File**: `app/services/batch_embeddings.py`
```python
class BatchEmbeddingService:
    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int | None = None
    ) -> list[tuple[EmbeddingVector, int]]:  # (vector, latency_ms)
        """Embed multiple texts in batched API calls."""
```

#### Task 3.2: Integrate with Backpressure
- Use existing `AdaptiveBatchSizer` for batch size adjustment
- Handle 429/5xx by reducing batch size
- Record batch metrics

#### Task 3.3: Update generate_embeddings_batch
**File**: `app/workflows/tasks/generate_embedding.py`
- Replace sequential calls with batch service
- Return embedding latency per chunk

---

### Phase 4: Hash Deduplication

#### Task 4.1: Enhanced Hash Function
**File**: `app/services/chunking/dedup.py`
```python
def compute_chunk_hash(
    text: str,
    model: str,
    model_version: str
) -> str:
    """Hash includes model info for re-embedding on model change."""
    content = f"{text.strip().lower()}|{model}|{model_version}"
    return hashlib.sha256(content.encode()).hexdigest()
```

#### Task 4.2: Add Repository Method
**File**: `app/db/repositories/chunk_repository.py`
```python
async def get_existing_hashes(
    self,
    analysis_id: UUID,
    hashes: list[str]
) -> set[str]:
    """Return hashes that already exist in database."""
```

#### Task 4.3: Create Dedup Task
**File**: `app/workflows/tasks/deduplicate_chunks.py`
```python
async def deduplicate_chunks(
    chunks: list[ChunkText],
    analysis_id: UUID,
    model: str,
    model_version: str
) -> tuple[list[ChunkText], DedupStats]:
    """Filter out chunks that already have embeddings."""
```

---

### Phase 5: Storage & Telemetry

#### Task 5.1: Update store_embeddings
**File**: `app/workflows/tasks/store_embeddings.py`
- Include `token_count`, `was_truncated`, `embedding_ms`
- Update metadata dict to include new fields

#### Task 5.2: Add Batch/Dedup Metrics
**File**: `app/services/metrics/service.py`
```python
def record_batch_embedding(
    self,
    batch_size: int,
    latency_ms: float,
    tokens_total: int
):
    """Record batch embedding metrics."""

def record_dedup_stats(
    self,
    total: int,
    skipped: int,
    embedded: int
):
    """Record deduplication statistics."""
```

#### Task 5.3: Update Workflow Integration
**File**: `app/workflows/graph_builder.py`
- Wire dedup task before embedding
- Update node connections

---

### Phase 6: Testing

#### Task 6.1: Unit Tests
**Files**:
- `tests/unit/services/test_batch_embeddings.py`
- `tests/unit/services/chunking/test_dedup_enhanced.py`
- `tests/unit/services/chunking/test_chunker_tokens.py`

#### Task 6.2: Integration Tests
**File**: `tests/integration/workflows/test_embedding_pipeline.py`
- Full pipeline test with dedup
- Re-processing test (verify skip)

---

## Dependency Graph

```
Phase 1 (Schema)
    │
    ├──▶ Phase 2 (Chunking)
    │        │
    │        ▼
    │    Phase 4 (Dedup)
    │        │
    │        ▼
    └──▶ Phase 3 (Batch Embed)
             │
             ▼
         Phase 5 (Storage)
             │
             ▼
         Phase 6 (Testing)
```

---

## Estimated Effort

| Phase | Tasks | Est. Hours |
|-------|-------|------------|
| 1. Schema | 3 | 2h |
| 2. Chunking | 3 | 3h |
| 3. Batch Embed | 3 | 4h |
| 4. Dedup | 3 | 3h |
| 5. Storage | 3 | 2h |
| 6. Testing | 2 | 4h |
| **Total** | **17** | **18h** |

---

## Files to Create/Modify

### New Files
- `app/services/batch_embeddings.py`
- `app/workflows/tasks/deduplicate_chunks.py`
- `alembic/versions/YYYYMMDD_add_chunk_metadata.py`
- `tests/unit/services/test_batch_embeddings.py`
- `tests/integration/workflows/test_embedding_pipeline.py`

### Modified Files
- `app/models/analysis_chunk.py`
- `app/core/config.py`
- `app/services/chunking/types.py` (or `chunker.py`)
- `app/services/chunking/chunker.py`
- `app/services/chunking/dedup.py`
- `app/db/repositories/chunk_repository.py`
- `app/workflows/tasks/generate_embedding.py`
- `app/workflows/tasks/store_embeddings.py`
- `app/workflows/tasks/chunk_content.py`
- `app/workflows/graph_builder.py`
- `app/services/metrics/service.py`
