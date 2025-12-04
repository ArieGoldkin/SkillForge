# Testing Strategy: Full-Text Search

## Overview

This document outlines the comprehensive testing strategy for the full-text search feature, including unit tests, integration tests, performance benchmarks, and accuracy validation.

## Testing Goals

1. **Correctness**: All search modes return relevant results
2. **Performance**: Meet latency targets (FTS < 500ms, Hybrid < 750ms, List < 200ms)
3. **Accuracy**: Top 5 results are relevant to the query
4. **Coverage**: Achieve ≥80% code coverage
5. **Reliability**: Handle edge cases and errors gracefully

## Test Coverage Target

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Repository Methods | 90% | High |
| API Endpoints | 85% | High |
| Schema Validation | 80% | Medium |
| Error Handling | 100% | High |
| Overall | ≥80% | Required |

## Test Pyramid

```
                    ┌─────────────┐
                    │   Manual    │
                    │   Testing   │  (5%)
                    └─────────────┘
                   ┌───────────────┐
                   │  Performance  │
                   │  Benchmarks   │  (10%)
                   └───────────────┘
               ┌───────────────────────┐
               │   Integration Tests   │
               │   (API + Database)    │  (20%)
               └───────────────────────┘
          ┌────────────────────────────────┐
          │        Unit Tests              │
          │  (Repository + Logic)          │  (65%)
          └────────────────────────────────┘
```

## Unit Tests (65% of test suite)

### Test File Structure

```
backend/tests/unit/
├── db/
│   └── repositories/
│       ├── test_analysis_repository.py (existing)
│       └── test_analysis_repository_search.py (new)
├── schemas/
│   └── test_library_schemas.py (new)
└── api/
    └── v1/
        └── test_library_logic.py (new)
```

### Repository Method Tests

**File**: `tests/unit/db/repositories/test_analysis_repository_search.py`

#### Test Cases for `search_by_text()`

```python
class TestSearchByText:
    """Tests for full-text search repository method."""

    @pytest.mark.asyncio
    async def test_search_by_text_success(self):
        """Test successful full-text search returns results with scores."""
        # Arrange: Mock session with sample results
        # Act: Execute search
        # Assert: Results match expected format and count
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_empty_query(self):
        """Test empty query returns empty list without DB call."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_whitespace_query(self):
        """Test query with only whitespace is treated as empty."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_with_content_type_filter(self):
        """Test content_type filter is applied correctly."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_with_status_filter(self):
        """Test status filter is applied correctly."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_with_both_filters(self):
        """Test combined content_type and status filters."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_limit_applied(self):
        """Test limit parameter restricts result count."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_special_characters(self):
        """Test query with special characters is handled safely."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_unicode(self):
        """Test query with unicode characters works correctly."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_ranking_order(self):
        """Test results are ordered by relevance score descending."""
        pass

    @pytest.mark.asyncio
    async def test_search_by_text_logs_metrics(self):
        """Test that search metrics are logged."""
        pass
```

#### Test Cases for `hybrid_search()`

```python
class TestHybridSearch:
    """Tests for hybrid search with RRF fusion."""

    @pytest.mark.asyncio
    async def test_hybrid_search_success(self):
        """Test successful hybrid search combines FTS and vector results."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_query(self):
        """Test hybrid search with empty query."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_invalid_weights(self):
        """Test invalid weights raise ValueError."""
        # Test fts_weight > 1
        # Test vector_weight < 0
        # Test both weights invalid
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_weight_sum_validation(self):
        """Test weights don't need to sum to 1.0."""
        # Should allow 0.7 + 0.3, 0.5 + 0.5, 0.9 + 0.1, etc.
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_rrf_calculation(self):
        """Test RRF scores are calculated correctly."""
        # Mock both result sets with known ranks
        # Verify final ranking matches expected RRF formula
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_deduplication(self):
        """Test results appearing in both searches are deduplicated."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(self):
        """Test filters are applied to both search methods."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_embedding_service_closed(self):
        """Test embedding service is properly closed after use."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_parallel_execution(self):
        """Test FTS and vector search run in parallel (asyncio.gather)."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_limit_applied(self):
        """Test final results respect limit parameter."""
        pass

    @pytest.mark.asyncio
    async def test_hybrid_search_logs_metrics(self):
        """Test comprehensive logging of search metrics."""
        pass
```

#### Test Cases for `list_analyses()`

```python
class TestListAnalyses:
    """Tests for paginated listing of analyses."""

    @pytest.mark.asyncio
    async def test_list_analyses_success(self):
        """Test successful listing returns results and total count."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_pagination(self):
        """Test limit and offset work correctly."""
        # Test first page (offset=0, limit=20)
        # Test second page (offset=20, limit=20)
        # Test partial page (offset=90, limit=20, only 10 results)
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_empty_results(self):
        """Test listing when no results match filters."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_total_count_accuracy(self):
        """Test total count is accurate regardless of pagination."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_order_by_created_at(self):
        """Test default ordering by created_at descending."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_order_by_updated_at(self):
        """Test ordering by updated_at."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_order_by_title(self):
        """Test ordering by title."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_invalid_order_by(self):
        """Test invalid order_by defaults to created_at."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_sql_injection_protection(self):
        """Test order_by parameter is validated against SQL injection."""
        # Test with malicious inputs like "created_at; DROP TABLE analyses;"
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_with_content_type_filter(self):
        """Test content_type filter."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_with_status_filter(self):
        """Test status filter."""
        pass

    @pytest.mark.asyncio
    async def test_list_analyses_logs_metrics(self):
        """Test listing metrics are logged."""
        pass
```

### Schema Validation Tests

**File**: `tests/unit/schemas/test_library_schemas.py`

```python
class TestLibrarySearchParams:
    """Tests for LibrarySearchParams schema."""

    def test_valid_params(self):
        """Test valid parameters are accepted."""
        pass

    def test_search_mode_default(self):
        """Test search_mode defaults to 'hybrid'."""
        pass

    def test_search_mode_validation(self):
        """Test invalid search_mode is rejected."""
        # Test: mode = "invalid" should fail
        pass

    def test_content_type_pattern(self):
        """Test content_type pattern validation."""
        # Valid: article, video, repo
        # Invalid: unknown, ""
        pass

    def test_status_pattern(self):
        """Test status pattern validation."""
        # Valid: pending, complete, failed
        # Invalid: unknown, ""
        pass

    def test_limit_range(self):
        """Test limit is between 1 and 100."""
        # Test: limit = 0 should fail
        # Test: limit = 101 should fail
        # Test: limit = 50 should pass
        pass

    def test_offset_non_negative(self):
        """Test offset must be >= 0."""
        # Test: offset = -1 should fail
        # Test: offset = 0 should pass
        pass


class TestLibraryItem:
    """Tests for LibraryItem schema."""

    def test_valid_item(self):
        """Test valid library item."""
        pass

    def test_missing_required_fields(self):
        """Test validation fails without required fields."""
        pass

    def test_relevance_score_optional(self):
        """Test relevance_score is optional."""
        pass

    def test_title_can_be_null(self):
        """Test title can be None."""
        pass


class TestLibraryResponse:
    """Tests for LibraryResponse schema."""

    def test_valid_response(self):
        """Test valid response structure."""
        pass

    def test_empty_results(self):
        """Test response with empty results list."""
        pass

    def test_total_matches_results_count(self):
        """Test total can be greater than results count (pagination)."""
        pass
```

## Integration Tests (20% of test suite)

### Test Database Setup

Use pytest fixtures to create test database with sample data:

```python
# conftest.py

@pytest.fixture(scope="session")
async def test_db():
    """Create test database with schema."""
    # Create test database
    # Run migrations
    # Yield connection
    # Cleanup

@pytest.fixture
async def sample_analyses(test_db):
    """Insert sample analyses for testing."""
    analyses = [
        {
            "url": "https://example.com/react-hooks",
            "title": "Introduction to React Hooks",
            "content_type": "article",
            "status": "complete",
            "raw_content": "React Hooks are a new addition in React 16.8...",
        },
        {
            "url": "https://example.com/vue-composition",
            "title": "Vue Composition API Guide",
            "content_type": "article",
            "status": "complete",
            "raw_content": "The Composition API is a new way to organize Vue components...",
        },
        # Add 20+ more diverse analyses
    ]
    # Insert into database
    # Trigger will auto-populate search_vector
    return analyses
```

### API Endpoint Tests

**File**: `tests/integration/api/test_library_endpoint.py`

```python
class TestLibraryEndpoint:
    """Integration tests for /api/v1/library endpoint."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_search_hybrid_e2e(self, async_client, sample_analyses):
        """End-to-end test for hybrid search."""
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "React hooks", "search_mode": "hybrid", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        # Verify React Hooks article is in top results
        titles = [item["title"] for item in data["results"]]
        assert any("React" in title for title in titles)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_search_fulltext_ranking(self, async_client, sample_analyses):
        """Test full-text search ranks by relevance."""
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "React hooks useState", "search_mode": "fulltext"},
        )

        data = response.json()
        # First result should have highest relevance_score
        scores = [item.get("relevance_score", 0) for item in data["results"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_list_pagination(self, async_client, sample_analyses):
        """Test pagination returns correct pages."""
        # Get first page
        page1 = await async_client.get(
            "/api/v1/library",
            params={"limit": 10, "offset": 0},
        )
        # Get second page
        page2 = await async_client.get(
            "/api/v1/library",
            params={"limit": 10, "offset": 10},
        )

        data1 = page1.json()
        data2 = page2.json()

        # Verify no overlap
        ids1 = {item["id"] for item in data1["results"]}
        ids2 = {item["id"] for item in data2["results"]}
        assert ids1.isdisjoint(ids2)

        # Verify same total count
        assert data1["total"] == data2["total"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_filter_by_content_type(self, async_client, sample_analyses):
        """Test content_type filter returns only matching types."""
        response = await async_client.get(
            "/api/v1/library",
            params={"content_type": "article"},
        )

        data = response.json()
        for item in data["results"]:
            assert item["content_type"] == "article"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_filter_by_status(self, async_client, sample_analyses):
        """Test status filter returns only matching statuses."""
        response = await async_client.get(
            "/api/v1/library",
            params={"status": "complete"},
        )

        data = response.json()
        for item in data["results"]:
            assert item["status"] == "complete"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_search_no_results(self, async_client, sample_analyses):
        """Test search with no matches returns empty results."""
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "xyznonexistentquery123", "search_mode": "fulltext"},
        )

        data = response.json()
        assert len(data["results"]) == 0
        assert data["total"] == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_search_special_characters(self, async_client):
        """Test search handles special characters safely."""
        special_queries = [
            "React & Vue",
            "C++ programming",
            "SQL'; DROP TABLE analyses; --",
            "search <script>alert('xss')</script>",
        ]

        for query in special_queries:
            response = await async_client.get(
                "/api/v1/library",
                params={"query": query, "search_mode": "fulltext"},
            )
            # Should not raise 500 error
            assert response.status_code in [200, 400]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_library_search_rate_limiting(self, async_client):
        """Test rate limiting is enforced (if implemented)."""
        # Make 100 rapid requests
        # Verify 429 Too Many Requests after threshold
        pass
```

## Performance Benchmarks (10% of test suite)

### Benchmark Test File

**File**: `tests/performance/test_search_benchmarks.py`

```python
class TestSearchPerformance:
    """Performance benchmarks for search functionality."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_fulltext_search_latency(self, async_client, benchmark_dataset):
        """Benchmark: Full-text search < 500ms (p95)."""
        latencies = []

        # Run 100 searches with different queries
        for query in benchmark_queries:
            start = time.time()
            await async_client.get(
                "/api/v1/library",
                params={"query": query, "search_mode": "fulltext", "limit": 20},
            )
            latencies.append((time.time() - start) * 1000)

        p95_latency = np.percentile(latencies, 95)
        assert p95_latency < 500, f"p95 latency: {p95_latency}ms (target: < 500ms)"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_hybrid_search_latency(self, async_client, benchmark_dataset):
        """Benchmark: Hybrid search < 750ms (p95)."""
        latencies = []

        for query in benchmark_queries:
            start = time.time()
            await async_client.get(
                "/api/v1/library",
                params={"query": query, "search_mode": "hybrid", "limit": 20},
            )
            latencies.append((time.time() - start) * 1000)

        p95_latency = np.percentile(latencies, 95)
        assert p95_latency < 750, f"p95 latency: {p95_latency}ms (target: < 750ms)"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_library_list_latency(self, async_client, benchmark_dataset):
        """Benchmark: Library listing < 200ms (p95)."""
        latencies = []

        for offset in range(0, 1000, 20):
            start = time.time()
            await async_client.get(
                "/api/v1/library",
                params={"limit": 20, "offset": offset},
            )
            latencies.append((time.time() - start) * 1000)

        p95_latency = np.percentile(latencies, 95)
        assert p95_latency < 200, f"p95 latency: {p95_latency}ms (target: < 200ms)"

    @pytest.mark.benchmark
    async def test_concurrent_search_load(self, async_client, benchmark_dataset):
        """Benchmark: System handles 50 concurrent searches."""
        import asyncio

        async def search_task():
            await async_client.get(
                "/api/v1/library",
                params={"query": "React", "search_mode": "hybrid"},
            )

        start = time.time()
        await asyncio.gather(*[search_task() for _ in range(50)])
        duration = time.time() - start

        # Should complete 50 searches in < 5 seconds
        assert duration < 5.0

    @pytest.mark.benchmark
    async def test_database_index_performance(self, test_db):
        """Benchmark: Verify GIN index is being used."""
        # Run EXPLAIN ANALYZE on full-text query
        query_plan = await test_db.execute(text("""
            EXPLAIN ANALYZE
            SELECT * FROM analyses
            WHERE search_vector @@ to_tsquery('english', 'React & hooks')
            LIMIT 20;
        """))

        plan_text = str(query_plan.fetchall())
        # Verify GIN index is in query plan
        assert "Bitmap Index Scan" in plan_text or "Index Scan" in plan_text
        assert "idx_analyses_search_vector" in plan_text
```

### Performance Test Dataset

Create realistic benchmark dataset:

```python
@pytest.fixture(scope="session")
def benchmark_dataset(test_db):
    """Create large dataset for performance testing."""
    # Insert 10,000 analyses with realistic content
    # Ensure search_vector is populated
    # Cover various content types and lengths
    pass

benchmark_queries = [
    "React hooks",
    "Vue composition API",
    "TypeScript generics",
    "Python async await",
    "Docker containers",
    "Kubernetes deployment",
    "GraphQL mutations",
    "PostgreSQL indexing",
    "Machine learning",
    "Neural networks",
]
```

## Accuracy Validation Tests

### Relevance Testing

**File**: `tests/accuracy/test_search_relevance.py`

```python
class TestSearchAccuracy:
    """Accuracy tests for search relevance."""

    @pytest.mark.accuracy
    @pytest.mark.asyncio
    async def test_fulltext_relevance_top5(self, async_client, curated_dataset):
        """Test that top 5 full-text results are relevant."""
        test_cases = [
            {
                "query": "React hooks useState",
                "expected_keywords": ["react", "hooks", "usestate"],
            },
            {
                "query": "Python async programming",
                "expected_keywords": ["python", "async", "await"],
            },
            {
                "query": "Docker container deployment",
                "expected_keywords": ["docker", "container", "deploy"],
            },
        ]

        for test_case in test_cases:
            response = await async_client.get(
                "/api/v1/library",
                params={
                    "query": test_case["query"],
                    "search_mode": "fulltext",
                    "limit": 5,
                },
            )

            data = response.json()
            results = data["results"][:5]

            # Verify at least 4 out of 5 top results contain expected keywords
            relevant_count = 0
            for result in results:
                content = (result.get("title", "") + " " + result.get("url", "")).lower()
                if any(keyword in content for keyword in test_case["expected_keywords"]):
                    relevant_count += 1

            assert relevant_count >= 4, f"Only {relevant_count}/5 results are relevant"

    @pytest.mark.accuracy
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, async_client, curated_dataset):
        """Test hybrid search combines FTS and semantic results."""
        # Query that should trigger both search methods
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "React hooks", "search_mode": "hybrid", "limit": 10},
        )

        data = response.json()
        # Should return results (not testing exact ranking here)
        assert len(data["results"]) > 0

    @pytest.mark.accuracy
    async def test_semantic_search_finds_similar_concepts(self, async_client, curated_dataset):
        """Test semantic search finds conceptually similar content."""
        # Search for "React hooks"
        # Should also find content about "Vue composition API" (similar concepts)
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "React hooks", "search_mode": "semantic", "limit": 10},
        )

        data = response.json()
        # Verify some results are about similar concepts (not exact match)
        # This tests semantic understanding
        pass
```

### Edge Case Tests

```python
class TestSearchEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_search_very_long_query(self, async_client):
        """Test search with very long query (> 1000 chars)."""
        long_query = "React " * 500  # 3000+ characters
        response = await async_client.get(
            "/api/v1/library",
            params={"query": long_query, "search_mode": "fulltext"},
        )
        # Should handle gracefully (truncate or return error)
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_search_unicode_multilingual(self, async_client):
        """Test search with multilingual unicode text."""
        queries = [
            "React フック",  # Japanese
            "React хуки",    # Russian
            "React 钩子",    # Chinese
        ]

        for query in queries:
            response = await async_client.get(
                "/api/v1/library",
                params={"query": query, "search_mode": "fulltext"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_empty_database(self, async_client, empty_db):
        """Test search returns empty results when database is empty."""
        response = await async_client.get(
            "/api/v1/library",
            params={"query": "React", "search_mode": "hybrid"},
        )

        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_pagination_beyond_total(self, async_client, sample_analyses):
        """Test pagination with offset > total results."""
        response = await async_client.get(
            "/api/v1/library",
            params={"limit": 20, "offset": 9999},
        )

        data = response.json()
        assert data["results"] == []
        assert data["total"] > 0  # Total should still be accurate
```

## Test Data Fixtures

### Curated Test Dataset

Create realistic test data for accuracy validation:

```python
curated_analyses = [
    {
        "title": "Introduction to React Hooks",
        "url": "https://example.com/react-hooks-intro",
        "content_type": "article",
        "raw_content": """
            React Hooks are functions that let you use state and other React features
            in functional components. The most commonly used hooks are useState and
            useEffect. Hooks were introduced in React 16.8 and have become the
            standard way to write React components.
        """,
    },
    {
        "title": "Vue Composition API Tutorial",
        "url": "https://example.com/vue-composition-api",
        "content_type": "article",
        "raw_content": """
            The Composition API is Vue 3's answer to React Hooks. It provides a more
            flexible way to organize component logic using functions like ref and
            reactive. This allows for better code reuse and organization.
        """,
    },
    {
        "title": "Python Async/Await Guide",
        "url": "https://example.com/python-async-await",
        "content_type": "article",
        "raw_content": """
            Asynchronous programming in Python using async and await keywords allows
            you to write concurrent code. The asyncio library provides the foundation
            for async programming in Python 3.7+.
        """,
    },
    # Add 20+ more diverse, realistic analyses
]
```

## Test Execution

### Running Tests Locally

```bash
# Run all tests
pytest backend/tests/

# Run only unit tests
pytest backend/tests/unit/

# Run integration tests (requires test database)
pytest backend/tests/integration/ -m integration

# Run performance benchmarks
pytest backend/tests/performance/ -m benchmark

# Run accuracy tests
pytest backend/tests/accuracy/ -m accuracy

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest backend/tests/unit/db/repositories/test_analysis_repository_search.py -v
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run migrations
        run: alembic upgrade head

      - name: Run unit tests
        run: pytest backend/tests/unit/ -v --cov=app

      - name: Run integration tests
        run: pytest backend/tests/integration/ -m integration -v

      - name: Check coverage threshold
        run: pytest --cov=app --cov-fail-under=80

      - name: Run performance benchmarks
        run: pytest backend/tests/performance/ -m benchmark

      - name: Upload coverage report
        uses: codecov/codecov-action@v3
```

## Monitoring and Metrics

### Test Metrics to Track

1. **Code Coverage**: ≥80% overall, ≥90% for critical paths
2. **Test Execution Time**: < 5 minutes for full suite
3. **Flaky Test Rate**: < 1% of tests
4. **Test Pass Rate**: ≥99% on main branch

### Performance Metrics Dashboard

Track these metrics over time:

- Full-text search latency (p50, p95, p99)
- Hybrid search latency (p50, p95, p99)
- Library listing latency (p50, p95, p99)
- Database connection pool usage
- GIN index size and bloat
- Query plan cache hit rate

## Manual Testing Checklist

After automated tests pass, perform manual validation:

- [ ] Test search in browser with various queries
- [ ] Verify pagination works correctly in UI
- [ ] Test search with different content_type filters
- [ ] Verify search results are relevant and well-ranked
- [ ] Test search with very long queries
- [ ] Test search with special characters and unicode
- [ ] Verify API documentation is accurate (Swagger UI)
- [ ] Check logs for errors or warnings
- [ ] Monitor performance during load test
- [ ] Verify database indexes are being used (EXPLAIN ANALYZE)

## Troubleshooting Failed Tests

### Common Issues

**Issue**: Full-text search tests fail with "column search_vector does not exist"
**Solution**: Run migration: `alembic upgrade head`

**Issue**: Performance benchmarks fail intermittently
**Solution**: Run benchmarks in isolation, check database load, increase timeout

**Issue**: Hybrid search tests fail with embedding service errors
**Solution**: Check OpenAI API key, mock embedding service in unit tests

**Issue**: Integration tests fail with connection errors
**Solution**: Verify test database is running, check connection string

## Test Maintenance

### Regular Tasks

- **Weekly**: Review and update test data fixtures
- **Monthly**: Analyze flaky tests and improve reliability
- **Quarterly**: Review coverage gaps and add missing tests
- **Per Release**: Run full test suite including manual tests

### Test Debt Tracking

Track test improvements needed:

- [ ] Add more edge case tests for unicode queries
- [ ] Improve semantic search accuracy tests
- [ ] Add load testing with realistic traffic patterns
- [ ] Create visual regression tests for search UI
- [ ] Add chaos testing for database failures

## Success Criteria

Tests are considered successful when:

1. ✅ Unit test coverage ≥ 90% for repository methods
2. ✅ Integration tests pass consistently (< 1% flaky)
3. ✅ Performance benchmarks meet all targets
4. ✅ Accuracy tests show ≥80% relevance in top 5 results
5. ✅ All edge cases handled gracefully
6. ✅ CI/CD pipeline passes all checks
7. ✅ Manual testing checklist completed
8. ✅ No critical bugs found in production monitoring
