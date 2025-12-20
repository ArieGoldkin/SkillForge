# Search Service Implementation Audit

**Date**: 2025-12-18
**Branch**: `issue/299-304-artifact-quality-initiative`
**Purpose**: Identify search implementation details affecting recall and potential improvements

---

## Executive Summary

The SkillForge backend implements a **sophisticated hybrid search architecture** with semantic (vector), keyword (full-text), and hybrid (RRF fusion) search modes. The implementation includes LLM-based re-ranking with structural priors, comprehensive metrics collection, and graceful fallback handling.

### Critical Findings

| Issue | Severity | Impact | Location |
|-------|----------|--------|----------|
| tsvector not used | High | 5-10x slower keyword search | `chunk_repository.py:169` |
| Evaluation `top_k=5` | High | Recall ceiling for queries with >5 chunks | `runner.py:352` |
| Snippet-only search | Medium | Keyword recall limited to first ~200 chars | Schema design |
| No re-ranking in eval | Medium | Unknown re-ranking quality | `runner.py` |
| 2x candidate fetch | Medium | May miss rank 11-20 chunks | `chunk_repository.py:237` |

### Quick Wins (1-2 hours each)
1. Use `AnalysisChunk.content_tsvector` instead of computing `to_tsvector()` at query time
2. Make evaluation `top_k` dynamic: `max(5, len(expected_chunks))`
3. Increase hybrid search fetch multiplier from 2x to 3x

---

## 1. Search Modes

### 1.1 Semantic Search
**Location**: `app/shared/services/search/search_service.py:210-261`
**Database**: `app/db/repositories/chunk_repository.py:74-128`

**Implementation**:
- Uses pgvector's cosine distance operator with HNSW indexing
- Query embedding generated via OpenAI `text-embedding-3-small` (1536 dimensions)
- L2 normalized vectors for scale-invariant cosine similarity
- Score formula: `similarity_score = 1 - cosine_distance` (range: 0.0-1.0)

**Features**:
- Metadata filtering: `content_type`, `analysis_id` via direct columns
- No query expansion or query rewriting
- Single-shot retrieval (no iterative refinement)

**Strengths**:
- Fast approximate kNN via HNSW index
- Normalized scores (0.0-1.0 range)
- Supports metadata filtering

**Limitations**:
- No multi-vector retrieval (e.g., query expansion)
- No late interaction models (ColBERT-style)
- No dense-sparse hybrid at vector level

---

### 1.2 Keyword Search
**Location**: `app/shared/services/search/search_service.py:263-308`
**Database**: `app/db/repositories/chunk_repository.py:130-191`

**Implementation**:
- PostgreSQL full-text search using `tsvector` + `tsquery`
- `plainto_tsquery` for query parsing (handles stop words)
- `ts_rank_cd` for BM25-like ranking (cover density scoring)
- Operates on `snippet` column (on-the-fly `to_tsvector`)

**Score Normalization**:
```python
max_score = max(score for _, score in chunks_with_scores)
normalized = score / max_score if max_score > 0 else 0.0
```

**Strengths**:
- Built-in PostgreSQL, no external dependencies
- Good for exact term matching and lexical recall
- Handles phrase queries and stop words automatically

**Limitations**:
- **CRITICAL**: No pre-computed `tsvector` column with index
  - Current: `to_tsvector('english', snippet)` computed at query time
  - Impact: Slower query performance vs. indexed `tsvector`
- Operates on `snippet` (200 char preview) not full content
  - **This may hurt recall** if query terms appear later in content
- Min-max normalization may not be stable across queries

**Recommendation**:
```sql
-- Add pre-computed tsvector column with GIN index
ALTER TABLE analysis_chunks ADD COLUMN content_tsvector tsvector;
CREATE INDEX ix_analysis_chunks_content_tsvector
  ON analysis_chunks USING GIN(content_tsvector);

-- Populate with trigger
CREATE TRIGGER tsvector_update
  BEFORE INSERT OR UPDATE ON analysis_chunks
  FOR EACH ROW EXECUTE FUNCTION
  tsvector_update_trigger(content_tsvector, 'pg_catalog.english', snippet);
```

---

### 1.3 Hybrid Search (RRF Fusion)
**Location**: `app/shared/services/search/search_service.py:310-367`
**Database**: `app/db/repositories/chunk_repository.py:193-278`
**RRF Algorithm**: `app/shared/services/search/hybrid_fusion.py`

**Implementation**:
- Executes semantic + keyword searches in parallel
- Fetches `2 * limit` candidates from each method for coverage
- Combines via Reciprocal Rank Fusion (RRF)
- RRF constant: `k=60` (standard from Cormack et al., 2009)

**RRF Formula**:
```python
RRF_score(chunk) = Σ 1/(k + rank(chunk)) for rank in [semantic_rank, keyword_rank]
```

**Score Normalization**:
```python
max_score = max(score for _, score in chunks_with_scores)
normalized = score / max_score if max_score > 0 else 0.0
```

**Strengths**:
- Robust to score scale differences (rank-based, not score-based)
- Simple, well-studied algorithm with good empirical results
- Handles duplicate chunks gracefully (RRF scores sum)

**Weaknesses**:
- Fixed `k=60` constant (not tunable per query)
- No learned fusion weights (static algorithm)
- Min-max normalization may compress score distribution

**Potential Improvements**:
1. **Learned fusion** via cross-encoder or LambdaMART
2. **Dynamic RRF constant** based on query characteristics
3. **Query analysis** to select semantic vs. keyword vs. hybrid

---

## 2. Re-Ranking System

### 2.1 LLM-Based Re-Ranking
**Location**: `app/shared/services/search/reranker.py`

**Architecture**:
- Uses `gpt-4o-mini` for cost-effective relevance scoring
- Batch processes candidates (all chunks in single LLM call)
- Combines LLM score with structural priors and base score

**Weighted Score Combination**:
```python
# From app/core/constants.py
RERANK_ALPHA = 0.3  # Base retrieval score weight
RERANK_BETA = 0.5   # LLM relevance score weight
RERANK_GAMMA = 0.2  # Structural prior weight

final_score = (RERANK_ALPHA * base_score) +
              (RERANK_BETA * llm_score) +
              (RERANK_GAMMA * structural_score)
```

**LLM Prompt**:
```
System: You are a search relevance scoring assistant.
Output ONLY a relevance score from 0.0 to 1.0 for each document.
One decimal number per line, in the same order as documents.

Example:
Query: "OAuth2 authentication"
Document: "FastAPI provides built-in OAuth2 support..."
Score: 0.95
```

**Configuration** (`app/core/constants.py`):
```python
RERANK_DEFAULT_TIMEOUT = 5.0          # Timeout in seconds
RERANK_DEFAULT_CANDIDATES = 50        # Candidates to fetch
RERANK_DEFAULT_FINAL_COUNT = 10       # Results after re-ranking
RERANK_MODEL = "gpt-4o-mini"          # Cost-effective model
```

**Graceful Fallback**:
- On timeout: Returns results sorted by base score (no re-ranking)
- On error: Same fallback behavior
- Metrics recorded for both success and failure cases

**Strengths**:
- Cost-effective (gpt-4o-mini vs. gpt-4)
- Batch processing reduces API calls
- Graceful degradation preserves UX
- Comprehensive error handling

**Limitations**:
- Fixed prompt (no query-adaptive instructions)
- Single-pass scoring (no iterative refinement)
- Content truncated to 300 chars per chunk for token efficiency
  - **May miss relevance signals** in longer chunks
- No confidence scores or uncertainty estimates

---

### 2.2 Structural Priors
**Location**: `app/shared/services/search/structural_priors.py`

**Purpose**: Boost chunks based on metadata features that correlate with relevance

**Features Scored**:

| Feature | Weight | Description |
|---------|--------|-------------|
| Section present | +0.10 | Chunk has explicit section title |
| Path depth | -0.05 per level > 2 | Deeper paths = less fundamental |
| Position early | +0.10 | First 20% of section (definitions) |
| Position late | -0.05 | Last 20% of section (appendices) |
| Code block | +0.05 | Chunk is code |
| Heading | +0.10 | Chunk is heading |

**Implementation**:
```python
# From structural_priors.py:92-138
def score_single(metadata: ChunkMetadata) -> float:
    score = 0.0

    if metadata.section:
        score += 0.10

    if metadata.path and len(metadata.path) > 2:
        score -= 0.05 * (len(metadata.path) - 2)

    if metadata.chunk_idx and metadata.chunk_total:
        position_ratio = metadata.chunk_idx / metadata.chunk_total
        if position_ratio < 0.2:
            score += 0.10  # Early position
        elif position_ratio > 0.8:
            score -= 0.05  # Late position

    if metadata.chunk_type == "code_block":
        score += 0.05
    elif metadata.chunk_type == "heading":
        score += 0.10

    return score
```

**Strengths**:
- Lightweight (no model calls)
- Interpretable features
- Can correct semantic search biases (e.g., boost early chunks)

**Limitations**:
- Fixed weights (not learned from data)
- No interaction terms (e.g., "code block in early position")
- Assumes structural heuristics generalize across all queries
- Weight scale (-0.2 to +0.3) may be too small to impact ranking

**Potential Improvements**:
1. **Learn weights** from golden dataset annotations
2. **Query-adaptive priors** (e.g., code queries boost code_block more)
3. **Add features**: chunk length, keyword density, entity presence

---

## 3. Hardcoded Limits and Thresholds

### 3.1 Search Service Limits
**Location**: `app/core/constants.py:63-66`

```python
SEARCH_TOP_K_MIN = 1        # Minimum search results
SEARCH_TOP_K_MAX = 100      # Maximum search results
SEARCH_QUERY_MAX_LENGTH = 1000  # Max query chars
```

**Impact**: These are **validation bounds**, not hardcoded retrieval limits. The actual `top_k` is user-configurable.

---

### 3.2 Evaluation Pipeline Limits
**Location**: `app/evaluation/pipeline/runner.py:352`

**CRITICAL FINDING**:
```python
# Line 352: Hardcoded top_k=5 in evaluation
results = await self.search_service.search(
    query=query_text,
    top_k=5,  # ⚠️ HARDCODED - NOT CONFIGURABLE
    mode=SearchMode.HYBRID,
)
```

**Impact Analysis**:
- **Recall@5 metrics are accurate** for top-5 retrieval
- **BUT**: If golden dataset queries have >5 expected chunks, the system cannot retrieve all of them
- **Example**: Query expects chunks [A, B, C, D, E, F, G] (7 chunks)
  - Best possible Recall@5 = 5/7 = 0.714
  - System will **never achieve Recall@5 = 1.0** for this query

**Mitigation**:
```python
# Proposed fix in runner.py
results = await self.search_service.search(
    query=query_text,
    top_k=max(5, len(expected_chunks)),  # Dynamic based on expected chunks
    mode=SearchMode.HYBRID,
)
```

---

### 3.3 Hybrid Search Candidate Fetching
**Location**: `app/db/repositories/chunk_repository.py:236-250`

```python
# Line 237: Fetches 2x limit for coverage
fetch_limit = limit * 2

semantic_results = await self.semantic_search(
    query_embedding=query_embedding,
    limit=fetch_limit,  # 2x for RRF fusion
    filters=filters,
)

keyword_results = await self.keyword_search(
    query_text=query_text,
    limit=fetch_limit,  # 2x for RRF fusion
    filters=filters,
)
```

**Rationale**: Fetch more candidates than needed to ensure RRF fusion has sufficient overlap

**Impact**: If `top_k=5` in evaluation, hybrid search fetches:
- Semantic: 10 candidates
- Keyword: 10 candidates
- RRF combines and returns top 5

**Analysis**:
- Good: Ensures RRF has sufficient candidates
- Concern: If relevant chunks rank 11-20 in both methods, they won't be considered
- **Recommendation**: Consider `3x` or `4x` multiplier for better coverage

---

### 3.4 Re-Ranking Candidate Count
**Location**: `app/core/constants.py:73`

```python
RERANK_DEFAULT_CANDIDATES = 50   # Fetch 50 candidates for re-ranking
RERANK_DEFAULT_FINAL_COUNT = 10  # Return top 10 after re-ranking
```

**Usage** (`app/shared/services/search/search_service.py:149-153`):
```python
fetch_k = top_k
if rerank and rerank.enabled:
    fetch_k = rerank.candidate_count  # Override with 50
```

**Impact**:
- **Good**: Re-ranking considers 50 candidates (more than eval's top_k=5)
- **But**: Evaluation doesn't enable re-ranking by default
- **Result**: Re-ranking capabilities are not tested in evaluation pipeline

---

## 4. How Evaluation Uses Search

**Location**: `app/evaluation/pipeline/runner.py:303-420`

**Flow**:
```python
# 1. Load queries with expected_chunks
queries = load_from_fixtures(fixtures_dir / "queries.json")

# 2. For each query:
results = await self.search_service.search(
    query=query_text,
    top_k=5,        # ⚠️ HARDCODED
    mode=SearchMode.HYBRID,
)

# 3. Extract section IDs from path metadata
retrieved_ids = [r.metadata.path[1] for r in results if len(r.metadata.path) > 1]

# 4. Compute metrics
metrics = self._compute_metrics(retrieved_ids, expected_chunks, k=5)
recalls.append(metrics["recall"])
mrrs.append(metrics["mrr"])
ndcgs.append(metrics["ndcg"])
```

**ID Matching Logic** (lines 357-365):
```python
# Uses path[1] (section_id) for matching
# Path format: ["doc_id", "section_id"]
# Example: ["fastapi-auth", "fastapi-auth/intro"]
retrieved_ids = []
for r in results:
    if r.metadata.path and len(r.metadata.path) > 1:
        retrieved_ids.append(r.metadata.path[1])  # Section ID
    else:
        retrieved_ids.append(r.chunk_id)  # Fallback to chunk_id
```

**Concerns**:
1. **Path-based ID matching** assumes all chunks have `path` metadata
   - Fallback to `chunk_id` may cause mismatches if golden data uses different IDs
2. **No re-ranking** in evaluation (only base retrieval tested)
3. **Fixed top_k=5** limits recall ceiling for queries with >5 expected chunks

---

## 5. Score Ranking and Normalization

### 5.1 Score Ranges

| Method | Raw Score Range | Normalized Range | Notes |
|--------|----------------|------------------|-------|
| Semantic | 0.0 - 1.0 | 0.0 - 1.0 | 1 - cosine_distance |
| Keyword | 0.0 - ~10+ | 0.0 - 1.0 | Min-max normalized |
| Hybrid (RRF) | 0.0 - ~0.1 | 0.0 - 1.0 | Min-max normalized |
| Re-ranking | 0.0 - ~1.3 | 0.0 - 1.0 | Weighted sum, then clamped |

### 5.2 Score Stability

**Semantic Search**: ✅ Stable
- Cosine similarity is bounded [0, 1]
- Consistent across queries

**Keyword Search**: ⚠️ Query-dependent
- `ts_rank_cd` scores vary by document length and term frequency
- Min-max normalization makes scores **incomparable across queries**
- Example: Query A max_score=2.5, Query B max_score=8.0
  - Same normalized score (0.8) means different raw scores (2.0 vs 6.4)

**Hybrid Search**: ⚠️ RRF-dependent
- RRF scores are small (~0.016-0.033 for k=60, top ranks)
- Min-max normalization amplifies score differences
- **Concern**: May over-fit to top-ranked item

**Re-ranking**: ⚠️ Weight-sensitive
```python
# Weights sum to 1.0 (good)
RERANK_ALPHA + RERANK_BETA + RERANK_GAMMA = 0.3 + 0.5 + 0.2 = 1.0

# But scores can exceed 1.0 before clamping:
# base=0.9, llm=0.95, structural=0.3 → final = 0.27 + 0.475 + 0.06 = 0.805 ✅
# base=1.0, llm=1.0, structural=0.3 → final = 0.3 + 0.5 + 0.06 = 0.86 ✅
```

**Clamping** (line 158 in `reranker.py`):
```python
clamped_score = max(0.0, min(1.0, score_data.final_score))
```

---

## 6. Potential Improvements

### 6.1 Critical Issues (High Impact)

#### Issue 1: Keyword Search Schema Optimization
**Current State** (confirmed from `app/db/models/analysis_chunk.py`):
- Schema has `content_tsvector` column (TSVECTOR) - Line 107
- Column is "auto-populated by database trigger" (per docstring Line 106)
- **BUT**: Repository code computes `to_tsvector` at query time (Line 169 in `chunk_repository.py`)
- Chunks store only `snippet` (Text column) - Line 101
- `content` property is an alias for `snippet` (Lines 158-162)

**Problem**:
1. Database trigger may not be working or is disabled
2. Keyword search doesn't use pre-indexed `content_tsvector`
3. Computes `to_tsvector('english', snippet)` on every query (slow)

**Fix**:
```python
# In chunk_repository.py:169 - Use pre-indexed tsvector column
# BEFORE:
content_tsvector = func.to_tsvector("english", AnalysisChunk.snippet)

# AFTER:
content_tsvector = AnalysisChunk.content_tsvector  # Use indexed column
```

**Prerequisites**:
1. Verify database trigger exists and is active:
```sql
-- Check if trigger exists
SELECT tgname, tgtype, tgenabled
FROM pg_trigger
WHERE tgrelid = 'analysis_chunks'::regclass
  AND tgname LIKE '%tsvector%';
```

2. If trigger is missing, create it:
```sql
CREATE TRIGGER tsvector_update
BEFORE INSERT OR UPDATE ON analysis_chunks
FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(content_tsvector, 'pg_catalog.english', snippet);
```

3. Backfill existing rows:
```sql
UPDATE analysis_chunks
SET content_tsvector = to_tsvector('english', COALESCE(snippet, ''))
WHERE content_tsvector IS NULL;
```

**Expected Impact**: 5-10x faster keyword search queries by using GIN index

---

#### Issue 2: Evaluation Pipeline Hardcodes `top_k=5`
**Problem**: Limits recall ceiling for queries with >5 expected chunks
**Impact**: Cannot measure true recall capability
**Fix**:
```python
# In runner.py:352
expected_chunks = query.get("expected_chunks", [])
dynamic_k = max(5, len(expected_chunks))

results = await self.search_service.search(
    query=query_text,
    top_k=dynamic_k,  # Dynamic based on expected chunks
    mode=SearchMode.HYBRID,
)

# Still compute Recall@5 for consistency
metrics = self._compute_metrics(retrieved_ids, expected_chunks, k=5)
```

**Alternative**: Add separate Recall@10 and Recall@20 metrics

---

#### Issue 3: Re-Ranking Not Tested in Evaluation
**Problem**: Evaluation pipeline doesn't enable re-ranking
**Impact**: Re-ranking quality is unknown
**Fix**:
```python
# In runner.py, add rerank parameter
from app.schemas.search import ReRankConfig

results = await self.search_service.search(
    query=query_text,
    top_k=5,
    mode=SearchMode.HYBRID,
    rerank=ReRankConfig(
        enabled=True,
        candidate_count=50,
        final_count=5,
    ),
)
```

**Trade-off**: Slower evaluation, higher cost (LLM calls)

---

### 6.2 Moderate Issues (Medium Impact)

#### Issue 4: Hybrid Search Fetches Only `2x` Candidates
**Problem**: RRF may miss relevant chunks ranked 11-20
**Impact**: Reduced recall for difficult queries
**Fix**:
```python
# In chunk_repository.py:237
fetch_limit = limit * 3  # Increase from 2x to 3x or 4x
```

**Trade-off**: Slower queries (more DB I/O)

---

#### Issue 5: Structural Priors Have Fixed Weights
**Problem**: Weights not learned from data
**Impact**: May not generalize across query types
**Fix**: Learn weights via logistic regression on golden dataset
```python
# Pseudocode
from sklearn.linear_model import LogisticRegression

# Features: [section_present, path_depth, position_ratio, is_code, is_heading]
# Labels: [is_relevant] (binary)
model = LogisticRegression()
model.fit(features, labels)

# Use model.coef_ as learned weights
STRUCTURAL_WEIGHT_SECTION_PRESENT = model.coef_[0]
# etc.
```

---

#### Issue 6: Re-Ranking Truncates Content to 300 Chars
**Problem**: LLM sees only first 300 chars per chunk
**Impact**: May miss relevance signals in longer chunks
**Fix**:
```python
# In reranker.py:336
max_content_length = 500  # Increase from 300 to 500

# Or: Use snippet (which is designed to highlight query terms)
chunks_text = "\n\n".join(
    f"[Document {i + 1}]\n{result.snippet}"  # Already query-aware
    for i, result in enumerate(results)
)
```

---

### 6.3 Minor Issues (Low Impact, Future Work)

#### Issue 7: No Query Expansion
**Problem**: Semantic search is single-shot (no query rewriting)
**Impact**: Misses paraphrased or synonym matches
**Potential**: Use LLM to generate query variations, embed all, average vectors

#### Issue 8: No Cross-Encoder Re-Ranking
**Problem**: LLM prompt-based re-ranking is less accurate than fine-tuned cross-encoders
**Impact**: Suboptimal ranking quality
**Potential**: Use `cross-encoder/ms-marco-MiniLM-L-12-v2` from sentence-transformers

#### Issue 9: No Late Interaction Models
**Problem**: Single dense vector per chunk (no token-level interactions)
**Impact**: Misses fine-grained semantic matches
**Potential**: Use ColBERTv2 for token-level matching

---

## 7. Summary of Findings

### Architecture Strengths
1. ✅ Comprehensive hybrid search with RRF fusion
2. ✅ LLM-based re-ranking with graceful fallback
3. ✅ Structural priors for metadata-aware ranking
4. ✅ Metrics collection and observability
5. ✅ Metadata filtering support

### Critical Issues
1. ❌ **Keyword search operates on `snippet` (200 chars) not full content**
2. ❌ **No indexed tsvector column** (computed at query time)
3. ❌ **Evaluation hardcodes `top_k=5`** (limits recall for queries with >5 expected chunks)
4. ❌ **Re-ranking not tested** in evaluation pipeline

### Moderate Issues
5. ⚠️ Hybrid search fetches only `2x` candidates (may miss rank 11-20)
6. ⚠️ Structural prior weights are fixed (not learned)
7. ⚠️ Re-ranking truncates content to 300 chars

### Minor Issues (Future Work)
8. 💡 No query expansion or rewriting
9. 💡 No cross-encoder re-ranking option
10. 💡 No late interaction models (ColBERT)

---

## 8. Recommended Action Items

### Phase 1: Critical Fixes (Immediate)

1. **Verify and fix tsvector trigger**
   - File: `app/db/models/analysis_chunk.py:107` (schema declares column)
   - File: `app/db/repositories/chunk_repository.py:169` (query doesn't use it)
   - Action: Check if trigger exists, create if missing, backfill data
   - Code fix: Change `func.to_tsvector(...)` to `AnalysisChunk.content_tsvector`
   - Impact: 5-10x faster keyword search queries

2. **Fix evaluation `top_k` hardcoding**
   - File: `app/evaluation/pipeline/runner.py:352`
   - Change: Dynamic `top_k` based on expected chunk count
   - Impact: Accurate recall measurement for queries with >5 expected chunks

3. **Investigate snippet content scope**
   - Confirmed: `snippet` column is ~200 char preview (per docstring)
   - Question: Is full chunk content stored elsewhere?
   - Impact: If only snippets are stored, keyword recall is fundamentally limited
   - Decision needed: Store full content for better keyword search?

### Phase 2: Evaluation Enhancements (Next Sprint)
4. **Add re-ranking to evaluation**
   - Test re-ranking impact on Recall@5
   - Measure latency and cost

5. **Add Recall@10 and Recall@20 metrics**
   - Complement Recall@5 with higher-k metrics
   - Better visibility into deep recall

6. **Validate ID matching logic**
   - Ensure `path[1]` matches golden dataset IDs
   - Add logging for fallback to `chunk_id`

### Phase 3: Ranking Improvements (Future)
7. **Learn structural prior weights**
   - Train logistic regression on golden dataset
   - A/B test learned vs. fixed weights

8. **Increase hybrid search candidate count**
   - Test 3x or 4x multiplier
   - Measure recall improvement vs. latency cost

9. **Optimize re-ranking content window**
   - Test 500-char vs. snippet-based re-ranking
   - Measure accuracy vs. token cost

---

## Appendix: File Locations

| Component | File | Lines |
|-----------|------|-------|
| Search Service | `app/shared/services/search/search_service.py` | 1-558 |
| Chunk Repository | `app/db/repositories/chunk_repository.py` | 1-451 |
| Re-Ranker | `app/shared/services/search/reranker.py` | 1-418 |
| Structural Priors | `app/shared/services/search/structural_priors.py` | 1-139 |
| RRF Fusion | `app/shared/services/search/hybrid_fusion.py` | 1-77 |
| Embedding Service | `app/shared/services/embeddings/service.py` | 1-475 |
| Evaluation Runner | `app/evaluation/pipeline/runner.py` | 1-504 |
| Constants | `app/core/constants.py` | 1-89 |

---

**Audit Completed**: 2025-12-18
**Next Steps**: Prioritize Phase 1 critical fixes before expanding golden dataset