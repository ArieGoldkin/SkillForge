# Issue #75: Full-Text Search for Analysis Library

## Status
- **Issue**: #75
- **Status**: Planning
- **Priority**: High
- **Story Points**: 8
- **Estimated Time**: 10.5 hours
- **Assignee**: Backend Team

## Summary

Implement hybrid full-text and semantic search for the library of analyses using PostgreSQL's full-text search (GIN index) combined with PGVector semantic search. This feature enables users to quickly find relevant analyses using keyword matching, semantic similarity, or a combination of both approaches.

## Problem Statement

Currently, the system only supports semantic search via vector embeddings. Users need the ability to:
- Search by exact keywords and phrases (full-text search)
- Search by semantic meaning (existing vector search)
- Combine both approaches for optimal relevance (hybrid search)
- Filter results by content type (article/video/repo) and status
- Paginate through large result sets efficiently

## Solution Overview

Implement a three-mode search system:

1. **Full-Text Search**: PostgreSQL GIN index for fast keyword matching
2. **Semantic Search**: Existing PGVector search (already implemented)
3. **Hybrid Search**: RRF (Reciprocal Rank Fusion) to combine both approaches with configurable weighting (0.7 × FTS + 0.3 × Vector)

## Acceptance Criteria

- [ ] PostgreSQL full-text search with GIN index on `analyses` table
- [ ] `search_vector` tsvector column with weighted fields (A: title, B: url, C: raw_content)
- [ ] Automatic search_vector updates via PostgreSQL trigger
- [ ] Hybrid search using RRF (Reciprocal Rank Fusion) algorithm
- [ ] `GET /api/v1/library` endpoint with pagination support
- [ ] Three search modes: `hybrid`, `fulltext`, `semantic`
- [ ] Filtering by `content_type` and `status`
- [ ] Performance targets met:
  - [ ] Full-text search: < 500ms for typical queries
  - [ ] Hybrid search: < 750ms for typical queries
  - [ ] Library listing: < 200ms for typical queries
- [ ] Test coverage ≥ 80%
- [ ] Top 5 results demonstrate relevance (accuracy test)
- [ ] Documentation updated with API specifications

## Related Issues

- Depends on: PGVector implementation (completed)
- Blocks: Advanced search UI (#TBD)
- Related: Search result ranking improvements (#TBD)

## Technical Stack

- **Database**: PostgreSQL with PGVector extension
- **Full-Text Search**: PostgreSQL tsvector with GIN index
- **Ranking Algorithm**: RRF (Reciprocal Rank Fusion)
- **Framework**: FastAPI with SQLAlchemy async
- **Testing**: pytest-asyncio

## Documentation

- [Architecture Overview](./ARCHITECTURE.md) - System design and data flow
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Step-by-step implementation guide
- [Testing Strategy](./TESTING_STRATEGY.md) - Test cases and performance benchmarks
- [API Specification](./API_SPEC.md) - Endpoint documentation with examples

## Timeline

| Phase | Description | Time | Status |
|-------|-------------|------|--------|
| 1 | Database Migration | 1.5h | Not Started |
| 2 | Repository Methods | 3h | Not Started |
| 3 | API Endpoint | 2.5h | Not Started |
| 4 | Performance Optimization | 1.5h | Not Started |
| 5 | Testing | 2h | Not Started |

**Total**: 10.5 hours

## Notes

- Existing semantic search infrastructure is already in place
- Migration must handle existing analyses (backfill search_vector)
- RRF weighting (0.7/0.3) can be tuned based on user feedback
- Consider adding search analytics for future optimization

## References

- [PostgreSQL Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch.html)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [Reciprocal Rank Fusion Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
