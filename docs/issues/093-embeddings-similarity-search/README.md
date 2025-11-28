# Issue #93: Implement Similarity Search Using Embeddings

**Status:** 🔄 **OPEN**  
**Assignee:** TBD  
**Story Points:** 8 pts  
**Priority:** MEDIUM  
**Created:** December 2024  
**GitHub Issue:** TBD (to be created)

---

## Issue Overview

**Title:** [🔵 Backend] Implement Similarity Search Using Stored Embeddings [8 pts]

**Description:**  
Currently, embeddings are generated and stored in `analyses.content_embedding` (1536-dim vectors) but are not used by the application. This issue implements similarity search functionality to enable:
- Finding similar analyses (library search)
- RAG (retrieval-augmented generation) for tutoring
- Semantic search across all analyses

**Labels:** `🔵 backend`, `✨ feature`, `medium`, `embeddings`, `vector-search`, `rag`

---

## Problem Statement

### Current State
- Embeddings are generated for every analysis (Issue #5 ✅ Complete)
- Embeddings are stored in PostgreSQL with PGVector extension
- Embeddings are **NOT used** by agents (agents receive raw text)
- No similarity search functionality exists

### Why Embeddings Aren't Used by Agents
- Agents analyze content directly via LLM prompts (raw text is sufficient)
- Embeddings serve a different purpose: **semantic similarity** and **retrieval**
- Agents don't need embeddings - they need the actual content text

### Use Cases for Embeddings
1. **Library Search**: Find analyses similar to a query or existing analysis
2. **RAG for Tutoring**: Retrieve relevant past analyses to provide context
3. **Content Discovery**: "Show me analyses about React" (semantic search)
4. **Duplicate Detection**: Find similar analyses to avoid redundant work

---

## Solution

### Phase 1: Similarity Search API Endpoint

**New Endpoint:** `GET /api/v1/analyses/similar`

**Query Parameters:**
- `analysis_id` (optional): Find analyses similar to this analysis
- `query` (optional): Semantic search query string
- `limit` (default: 10): Number of results to return
- `threshold` (default: 0.7): Minimum similarity score (0.0-1.0)

**Response:**
```json
{
  "results": [
    {
      "analysis_id": "uuid",
      "url": "https://example.com",
      "title": "Analysis Title",
      "similarity_score": 0.85,
      "content_type": "article"
    }
  ],
  "query_embedding_dimensions": 1536,
  "results_count": 10
}
```

### Phase 2: RAG Integration for Tutoring

**Enhancement:** Use similarity search to retrieve relevant past analyses when generating tutoring responses.

**Flow:**
1. User asks tutoring question
2. Generate embedding for question
3. Find top 5 similar analyses using cosine similarity
4. Include relevant excerpts in tutoring context
5. Generate response with retrieved context

### Phase 3: Library Search Enhancement

**Enhancement:** Add semantic search to library page.

**Features:**
- Search by semantic meaning (not just keywords)
- "Find analyses about React hooks" → returns relevant analyses
- Hybrid search: Combine semantic + keyword matching

---

## Implementation Details

### Database Query Pattern

**PGVector Cosine Similarity:**
```sql
SELECT 
    a.id,
    a.url,
    a.title,
    1 - (a.content_embedding <=> :query_embedding) as similarity_score
FROM analyses a
WHERE a.content_embedding IS NOT NULL
  AND 1 - (a.content_embedding <=> :query_embedding) >= :threshold
ORDER BY a.content_embedding <=> :query_embedding
LIMIT :limit;
```

**Note:** `<=>` is PGVector cosine distance operator (lower = more similar)

### New Service: `app/services/similarity_search.py`

**Functions:**
- `find_similar_analyses(analysis_id: UUID, limit: int, threshold: float) -> list[dict]`
- `search_by_query(query: str, limit: int, threshold: float) -> list[dict]`
- `generate_query_embedding(query: str) -> EmbeddingVector`

### Index Requirements

**PGVector Index for Performance:**
```sql
CREATE INDEX IF NOT EXISTS ix_analyses_content_embedding_cosine 
ON analyses 
USING ivfflat (content_embedding vector_cosine_ops)
WITH (lists = 100);
```

**Note:** IVFFlat index requires at least 100 rows for optimal performance.

---

## Acceptance Criteria

- [ ] Similarity search endpoint implemented (`GET /api/v1/analyses/similar`)
- [ ] Query-based semantic search works
- [ ] Analysis ID-based similarity search works
- [ ] PGVector index created for performance
- [ ] Integration tests for similarity search
- [ ] Documentation updated with usage examples
- [ ] Performance: <100ms for similarity queries (with index)

---

## Technical Details

### Dependencies
- ✅ PGVector extension (already enabled - Issue #3)
- ✅ Embedding service (already implemented - Issue #5)
- ✅ OpenAI text-embedding-3-small (1536 dimensions)

### Files to Create
- `backend/app/services/similarity_search.py` (NEW)
- `backend/app/api/v1/similarity.py` (NEW endpoint)
- `backend/tests/unit/services/test_similarity_search.py` (NEW)
- `backend/tests/integration/test_similarity_endpoint.py` (NEW)

### Files to Modify
- `backend/app/api/v1/__init__.py` (add similarity router)
- `backend/alembic/versions/xxx_add_similarity_index.py` (NEW migration)

---

## Related Issues

- **Issue #5:** Embedding Service Implementation (prerequisite ✅)
- **Issue #3:** Database Schema & Migrations (PGVector extension ✅)
- **Future:** RAG for Tutoring (depends on this issue)
- **Future:** Library Search Enhancement (depends on this issue)

---

## Future Enhancements

1. **Hybrid Search**: Combine semantic + keyword matching
2. **Re-ranking**: Use LLM to re-rank results for better relevance
3. **Metadata Filtering**: Filter by content_type, date range, etc.
4. **Batch Similarity**: Find similar analyses for multiple IDs at once
5. **Caching**: Cache query embeddings for common searches

---

## Notes

- Embeddings are stored but unused - this issue makes them useful
- Similarity search enables RAG patterns for tutoring
- Library search becomes semantic, not just keyword-based
- Foundation for future AI features (recommendations, clustering, etc.)
