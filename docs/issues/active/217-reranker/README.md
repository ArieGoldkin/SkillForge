# Issue #217: Re-ranker for Search Results

**Status:** IN PROGRESS
**Assignee:** Yonatan
**Sprint:** Sprint 8 - Embeddings & Search
**Story Points:** 5 pts
**GitHub Issue:** [#217](https://github.com/ArieGoldkin/SkillForge/issues/217)

---

## Issue Overview

**Title:** Sprint 8: Re-ranker for Search Results

**Description:**
Add a re-rank stage (LLM or cross-encoder) over top-N search results to improve precision, integrated with the search pipeline. Use structural priors (section/title/path, position) in scoring.

**Labels:** `backend`, `feature`, `sprint-8`, `python`, `search`, `llm`

**Dependencies:**
- Issue #216 (Retrieval & Search API) - Merged

---

## Architecture Overview

```
                        CURRENT PIPELINE (Issue #216)
                        ==============================
+-------------+     +------------------+     +----------------+
| Query       | --> | SearchService    | --> | ChunkRepository|
|             |     | (orchestration)  |     | (raw search)   |
+-------------+     +------------------+     +----------------+
                            |
                            v
                    +----------------+
                    | HybridFusion   |
                    | (RRF k=60)     |
                    +----------------+
                            |
                            v
                    +----------------+
                    | SearchResults  |
                    | (top_k=10)     |
                    +----------------+


                        PROPOSED PIPELINE (Issue #217)
                        ==============================
+-------------+     +------------------+     +----------------+
| Query       | --> | SearchService    | --> | ChunkRepository|
|             |     | (orchestration)  |     | (raw search)   |
+-------------+     +------------------+     +----------------+
                            |
                            v
                    +----------------+
                    | HybridFusion   |
                    | (RRF k=60)     |
                    +----------------+
                            |
                            v (top 50 candidates)
                    +------------------+
                    |    ReRanker      |  <-- NEW COMPONENT
                    | - LLM scoring    |
                    | - Structural     |
                    |   priors         |
                    +------------------+
                            |
                            v (top 5-10)
                    +----------------+
                    | SearchResults  |
                    +----------------+
```

---

## Design Decisions

### 1. LLM Re-ranker vs Cross-Encoder

| Factor | Cross-Encoder | LLM (GPT-5 Nano) |
|--------|---------------|------------------|
| Cost per 1K calls | ~$0.02-0.05 (self-hosted) | ~$0.70 (via API) |
| Latency | 50-200ms | 200-500ms |
| Quality | Good for semantic matching | Better query understanding |
| Setup Complexity | Requires HuggingFace/GPU | Uses existing OpenAI infra |
| Maintenance | Model updates, GPU management | Zero maintenance |

**Decision:** Use GPT-5 Nano ($0.05/$0.40 per 1M tokens) for cost-effective re-ranking with zero infrastructure overhead.

### 2. Integration Point

**Decision:** Integrate at SearchService level (not Repository) to:
- Keep repository focused on database operations
- Isolate re-ranking logic for testability
- Enable easy enable/disable via configuration

### 3. Score Combination

**Formula:**
```python
final_score = (0.3 * base_score) + (0.5 * llm_score) + (0.2 * structural_prior)
```

| Weight | Component | Description |
|--------|-----------|-------------|
| 0.3 (alpha) | Base score | RRF/semantic/keyword score from repository |
| 0.5 (beta) | LLM score | GPT-5 Nano relevance judgment |
| 0.2 (gamma) | Structural prior | Metadata-based boosts |

---

## Structural Priors

Metadata-based scoring using chunk attributes:

| Signal | Condition | Score Effect |
|--------|-----------|--------------|
| Section present | `metadata.section` is not empty | +0.10 boost |
| Path depth | depth > 2 | -0.05 per extra level |
| Early position | `chunk_idx / chunk_total < 0.2` | +0.10 boost |
| Late position | `chunk_idx / chunk_total > 0.8` | -0.05 penalty |
| Code block | `chunk_type == "code_block"` | +0.05 boost |
| Heading | `chunk_type == "heading"` | +0.10 boost |

---

## API Changes

### New Schema: `ReRankConfig`

```python
class ReRankConfig(BaseModel):
    """Configuration for optional re-ranking stage."""
    enabled: bool = False
    candidate_count: int = Field(default=50, ge=10, le=100)
    final_count: int = Field(default=10, ge=1, le=50)
    use_structural_priors: bool = True
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
```

### Updated `SearchRequest`

```python
class SearchRequest(BaseModel):
    query: str
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 10
    filters: SearchFilters | None = None
    rerank: ReRankConfig | None = None  # NEW - optional re-ranking
```

### Example API Request

```bash
# Without re-ranking (backwards compatible)
curl -X POST /api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "OAuth2 authentication", "mode": "hybrid", "top_k": 10}'

# With re-ranking enabled
curl -X POST /api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OAuth2 authentication",
    "mode": "hybrid",
    "top_k": 10,
    "rerank": {
      "enabled": true,
      "candidate_count": 50,
      "final_count": 10,
      "use_structural_priors": true,
      "timeout_seconds": 5.0
    }
  }'
```

---

## Fallback Behavior

On timeout or LLM error:
1. Log warning (not error) - graceful degradation expected
2. Return candidates sorted by base score only
3. User receives results without re-ranking

```python
try:
    async with asyncio.timeout(config.timeout_seconds):
        reranked = await self._score_with_llm(candidates, query)
        return reranked[:config.final_count]
except TimeoutError:
    logger.warning("rerank_timeout", timeout=config.timeout_seconds)
    return self._fallback_rank(candidates, config.final_count)
```

---

## File Structure

### New Files

| File | Purpose |
|------|---------|
| `app/services/search/reranker.py` | Core ReRanker class with LLM scoring |
| `app/services/search/structural_priors.py` | StructuralPriorScorer class |
| `tests/unit/services/search/test_reranker.py` | Unit tests for ReRanker |
| `tests/unit/services/search/test_structural_priors.py` | Unit tests for priors |

### Modified Files

| File | Changes |
|------|---------|
| `app/schemas/search.py` | Add `ReRankConfig` + update `SearchRequest` |
| `app/services/search/search_service.py` | Integrate ReRanker after search |
| `app/services/search/__init__.py` | Export ReRanker |
| `app/core/constants.py` | Add RERANK_* constants |
| `app/api/v1/search.py` | Pass rerank config to service |

---

## Constants

```python
# app/core/constants.py

# Re-ranking Configuration
RERANK_ALPHA = 0.3        # Weight for base retrieval score
RERANK_BETA = 0.5         # Weight for LLM relevance score
RERANK_GAMMA = 0.2        # Weight for structural prior score
RERANK_DEFAULT_TIMEOUT = 5.0  # Default timeout in seconds
RERANK_DEFAULT_CANDIDATES = 50  # Default candidate pool size
RERANK_MODEL = "gpt-5-nano"  # Cost-effective model for re-ranking
```

---

## Cost & Latency Analysis

### Cost per Search (with re-ranking)

| Component | Calculation | Cost |
|-----------|-------------|------|
| GPT-5 Nano Input | 50 chunks x 300 chars x 0.75 tokens = ~11,250 tokens | $0.0006 |
| GPT-5 Nano Output | 50 scores x 5 chars = ~250 tokens | $0.0001 |
| **Total per search** | ~11,500 tokens | **~$0.0007** |
| **Per 1000 searches** | ~11.5M tokens | **~$0.70** |

### Latency Impact

| Stage | p50 | p95 |
|-------|-----|-----|
| Base search (hybrid) | 50-100ms | 200ms |
| LLM re-ranking | 200-500ms | 1000ms |
| Structural priors | <1ms | <5ms |
| **Total with re-rank** | **250-600ms** | **~1200ms** |

---

## Test Checklist

- [ ] ReRanker reduces 50 candidates to 10
- [ ] Score combination: alpha*base + beta*llm + gamma*structural
- [ ] Timeout triggers fallback (base ranking)
- [ ] LLM error triggers fallback
- [ ] Equal scores have deterministic ordering (by chunk_id)
- [ ] Disabled config returns original results
- [ ] Backwards compatible (no rerank field = no re-ranking)
- [ ] Structural priors calculate correctly for each signal

---

## Acceptance Criteria

From issue #217:

- [x] Re-rank can be toggled per request/config
- [x] On failure/timeout, search still returns base results
- [ ] Tests cover happy path and fallback scenarios
- [ ] Docs capture model/prompt and latency/cost notes

---

## Implementation Sequence

1. Add constants to `app/core/constants.py`
2. Create `structural_priors.py` with `StructuralPriorScorer`
3. Create `reranker.py` with `ReRanker` class
4. Add `ReRankConfig` to `app/schemas/search.py`
5. Update `SearchService.search()` to use ReRanker
6. Update `app/api/v1/search.py` to pass config
7. Write unit tests for both new modules
8. Write integration test for end-to-end flow
9. Verify all existing tests pass
10. Create PR to dev
