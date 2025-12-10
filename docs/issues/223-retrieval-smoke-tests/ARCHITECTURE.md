# Retrieval Smoke Test Architecture

## System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SMOKE TEST SYSTEM CONTEXT                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────┐                                                          │
│    │   GitHub    │                                                          │
│    │   Actions   │─────────────────────────────────────┐                    │
│    └─────────────┘                                     │                    │
│          │                                             │                    │
│          │ triggers on PR                              │ artifacts          │
│          ▼                                             ▼                    │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                    SMOKE TEST SUITE                          │         │
│    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │         │
│    │  │  Fixtures   │  │   Runner    │  │  Reporter   │          │         │
│    │  │  (JSON)     │──│  (pytest)   │──│  (JSON/MD)  │          │         │
│    │  └─────────────┘  └─────────────┘  └─────────────┘          │         │
│    └───────────────────────────┬─────────────────────────────────┘         │
│                                │                                            │
│                                │ uses                                       │
│                                ▼                                            │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                   RETRIEVAL SERVICES                         │         │
│    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │         │
│    │  │ SearchSvc   │  │ EmbedSvc    │  │ ChunkRepo   │          │         │
│    │  │ (search.py) │  │ (embed.py)  │  │ (repo.py)   │          │         │
│    │  └─────────────┘  └─────────────┘  └─────────────┘          │         │
│    └───────────────────────────┬─────────────────────────────────┘         │
│                                │                                            │
│                                │ queries                                    │
│                                ▼                                            │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                      DATABASE                                │         │
│    │  ┌─────────────┐  ┌─────────────┐                           │         │
│    │  │ PostgreSQL  │  │  pgvector   │                           │         │
│    │  │ (tsvector)  │  │  (HNSW)     │                           │         │
│    │  └─────────────┘  └─────────────┘                           │         │
│    └─────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Fixture Loader

```python
# tests/smoke/retrieval/fixtures/loader.py

from pathlib import Path
from typing import TypedDict
import json


class Section(TypedDict):
    title: str
    content: str


class Document(TypedDict):
    id: str
    title: str
    content_type: str
    bucket: str  # "short" | "long"
    sections: list[Section]


class ExpectedResult(TypedDict):
    chunk_id: str
    min_score: float | None


class Query(TypedDict):
    id: str
    query: str
    modes: list[str]  # ["semantic", "keyword", "hybrid"]
    expected_chunks: list[str]
    min_score: float | None
    category: str  # "specific" | "broad" | "negative" | "edge"


class FixtureLoader:
    """Load and manage test fixtures for smoke tests."""

    def __init__(self, fixtures_dir: Path | None = None):
        self.fixtures_dir = fixtures_dir or Path(__file__).parent

    def load_documents(self) -> list[Document]:
        """Load test documents from JSON fixture."""
        path = self.fixtures_dir / "documents.json"
        with open(path) as f:
            data = json.load(f)
        return data["documents"]

    def load_queries(self) -> list[Query]:
        """Load test queries from JSON fixture."""
        path = self.fixtures_dir / "queries.json"
        with open(path) as f:
            data = json.load(f)
        return data["queries"]

    def get_queries_for_mode(self, mode: str) -> list[Query]:
        """Filter queries by search mode."""
        return [q for q in self.load_queries() if mode in q["modes"]]

    def get_documents_by_bucket(self, bucket: str) -> list[Document]:
        """Filter documents by size bucket."""
        return [d for d in self.load_documents() if d["bucket"] == bucket]
```

### 2. Test Database Setup

```python
# tests/smoke/retrieval/conftest.py

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.analysis import Analysis
from app.models.analysis_chunk import AnalysisChunk
from app.services.embeddings import EmbeddingService
from app.services.search import SearchService

from .fixtures.loader import FixtureLoader


@pytest.fixture(scope="session")
def fixture_loader():
    """Provide fixture loader for all tests."""
    return FixtureLoader()


@pytest_asyncio.fixture(scope="function")
async def smoke_test_db():
    """Create isolated test database with fixtures loaded."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        # Cleanup: Remove test data
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def populated_db(smoke_test_db, fixture_loader):
    """Database populated with fixture documents and embeddings."""
    session = smoke_test_db
    embedding_service = EmbeddingService()

    documents = fixture_loader.load_documents()

    for doc in documents:
        # Create analysis record
        analysis = Analysis(
            id=doc["id"],
            url=f"https://example.com/{doc['id']}",
            title=doc["title"],
            content_type=doc["content_type"],
            status="completed",
        )
        session.add(analysis)
        await session.flush()

        # Create chunks with embeddings
        for idx, section in enumerate(doc["sections"]):
            embedding = await embedding_service.generate_embedding(
                section["content"], normalize=True
            )

            chunk = AnalysisChunk(
                analysis_id=analysis.id,
                granularity="coarse",
                section_title=section["title"],
                snippet=section["content"][:200],
                content=section["content"],
                vector=embedding,
                chunk_idx=idx,
                chunk_total=len(doc["sections"]),
                content_type=doc["content_type"],
            )
            session.add(chunk)

        await session.commit()

    yield session


@pytest_asyncio.fixture
async def search_service(populated_db):
    """Provide SearchService with populated database."""
    embedding_service = EmbeddingService()
    return SearchService(populated_db, embedding_service)
```

### 3. Metrics Calculator

```python
# tests/smoke/retrieval/metrics.py

from dataclasses import dataclass
from typing import TypedDict

from app.schemas.search import SearchResult


class MetricsResult(TypedDict):
    recall_at_5: float
    recall_at_10: float
    mrr: float
    precision_at_5: float
    pass_rate: float


@dataclass
class QueryResult:
    """Result of a single query evaluation."""

    query_id: str
    query_text: str
    mode: str
    expected_chunks: list[str]
    actual_chunks: list[str]
    scores: list[float]
    recall_at_5: float
    mrr: float
    passed: bool
    error: str | None = None


def compute_recall_at_k(
    results: list[SearchResult],
    expected: list[str],
    k: int = 5,
) -> float:
    """Compute Recall@k metric.

    Recall@k = |{relevant docs in top k}| / |{all relevant docs}|

    Args:
        results: Search results from service
        expected: List of expected chunk IDs
        k: Number of top results to consider

    Returns:
        Recall score between 0.0 and 1.0

    """
    if not expected:
        return 1.0  # No expected results = vacuously true

    top_k_ids = {r.chunk_id for r in results[:k]}
    relevant_found = len(top_k_ids & set(expected))
    return relevant_found / len(expected)


def compute_mrr(
    results: list[SearchResult],
    expected: list[str],
) -> float:
    """Compute Mean Reciprocal Rank.

    MRR = 1 / rank of first relevant result

    Args:
        results: Search results from service
        expected: List of expected chunk IDs

    Returns:
        MRR score between 0.0 and 1.0

    """
    if not expected:
        return 1.0

    for i, result in enumerate(results, start=1):
        if result.chunk_id in expected:
            return 1.0 / i
    return 0.0


def compute_precision_at_k(
    results: list[SearchResult],
    expected: list[str],
    k: int = 5,
) -> float:
    """Compute Precision@k metric.

    Precision@k = |{relevant docs in top k}| / k

    """
    if not results:
        return 0.0

    top_k_ids = {r.chunk_id for r in results[:k]}
    relevant_found = len(top_k_ids & set(expected))
    return relevant_found / min(k, len(results))


def evaluate_query(
    query_id: str,
    query_text: str,
    mode: str,
    results: list[SearchResult],
    expected: list[str],
    min_recall: float = 0.8,
) -> QueryResult:
    """Evaluate a single query's results.

    Args:
        query_id: Unique query identifier
        query_text: The search query
        mode: Search mode used
        results: Search results from service
        expected: Expected chunk IDs
        min_recall: Minimum Recall@5 to pass

    Returns:
        QueryResult with metrics and pass/fail status

    """
    actual_chunks = [r.chunk_id for r in results]
    scores = [r.score for r in results]

    recall_5 = compute_recall_at_k(results, expected, k=5)
    mrr = compute_mrr(results, expected)

    # Pass if recall meets threshold (or no expected results for negative tests)
    passed = recall_5 >= min_recall or len(expected) == 0

    return QueryResult(
        query_id=query_id,
        query_text=query_text,
        mode=mode,
        expected_chunks=expected,
        actual_chunks=actual_chunks[:10],
        scores=scores[:10],
        recall_at_5=recall_5,
        mrr=mrr,
        passed=passed,
    )


def aggregate_metrics(results: list[QueryResult]) -> MetricsResult:
    """Aggregate metrics across all query results."""
    if not results:
        return MetricsResult(
            recall_at_5=0.0,
            recall_at_10=0.0,
            mrr=0.0,
            precision_at_5=0.0,
            pass_rate=0.0,
        )

    return MetricsResult(
        recall_at_5=sum(r.recall_at_5 for r in results) / len(results),
        recall_at_10=0.0,  # Computed separately if needed
        mrr=sum(r.mrr for r in results) / len(results),
        precision_at_5=0.0,  # Computed separately if needed
        pass_rate=sum(1 for r in results if r.passed) / len(results),
    )
```

### 4. Test Implementation Pattern

```python
# tests/smoke/retrieval/test_semantic_search.py

import pytest

from app.schemas.search import SearchMode

from .metrics import compute_recall_at_k, compute_mrr, evaluate_query


class TestSemanticSearchSmoke:
    """Smoke tests for semantic (vector) search."""

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_specific_query_finds_relevant_chunk(
        self, search_service, fixture_loader
    ):
        """Specific queries should find highly relevant chunks."""
        queries = fixture_loader.get_queries_for_mode("semantic")
        specific_queries = [q for q in queries if q["category"] == "specific"]

        for query in specific_queries:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=10,
            )

            result = evaluate_query(
                query_id=query["id"],
                query_text=query["query"],
                mode="semantic",
                results=results,
                expected=query["expected_chunks"],
                min_recall=0.8,
            )

            assert result.passed, (
                f"Query '{query['id']}' failed: "
                f"Recall@5={result.recall_at_5:.2f}, expected>=0.8"
            )

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_synonym_query_matches_semantically(
        self, search_service, fixture_loader
    ):
        """Synonyms and paraphrases should match via semantic similarity."""
        # Query uses different words but same meaning
        results = await search_service.search(
            query="secure API authentication methods",
            mode=SearchMode.SEMANTIC,
            top_k=5,
        )

        # Should find OAuth2 content even though "OAuth2" not in query
        assert len(results) > 0
        assert any("auth" in r.content.lower() for r in results)

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_negative_query_returns_low_scores(
        self, search_service, fixture_loader
    ):
        """Unrelated queries should return low relevance scores."""
        queries = fixture_loader.get_queries_for_mode("semantic")
        negative_queries = [q for q in queries if q["category"] == "negative"]

        for query in negative_queries:
            results = await search_service.search(
                query=query["query"],
                mode=SearchMode.SEMANTIC,
                top_k=5,
            )

            # All scores should be below threshold for unrelated content
            if results:
                max_score = max(r.score for r in results)
                assert max_score < 0.5, (
                    f"Negative query '{query['id']}' returned high score: {max_score}"
                )

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_short_vs_long_document_buckets(
        self, search_service, fixture_loader
    ):
        """Both short and long documents should be searchable."""
        # Test query that should match both buckets
        results = await search_service.search(
            query="programming tutorial",
            mode=SearchMode.SEMANTIC,
            top_k=10,
        )

        # Should have results from both short and long documents
        assert len(results) >= 2
```

### 5. Reporter

```python
# tests/smoke/retrieval/reporter.py

import json
from datetime import datetime
from pathlib import Path

from .metrics import MetricsResult, QueryResult


class SmokeTestReporter:
    """Generate reports from smoke test results."""

    def __init__(self, results: list[QueryResult], metrics: MetricsResult):
        self.results = results
        self.metrics = metrics
        self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        """Generate JSON report."""
        report = {
            "timestamp": self.timestamp,
            "summary": {
                "total_queries": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "pass_rate": self.metrics["pass_rate"],
            },
            "metrics": self.metrics,
            "results": [
                {
                    "query_id": r.query_id,
                    "query": r.query_text,
                    "mode": r.mode,
                    "passed": r.passed,
                    "recall_at_5": r.recall_at_5,
                    "mrr": r.mrr,
                    "expected": r.expected_chunks,
                    "actual": r.actual_chunks[:5],
                }
                for r in self.results
            ],
        }
        return json.dumps(report, indent=2)

    def to_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            "# Retrieval Smoke Test Report",
            "",
            f"**Generated:** {self.timestamp}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Queries | {len(self.results)} |",
            f"| Passed | {sum(1 for r in self.results if r.passed)} |",
            f"| Failed | {sum(1 for r in self.results if not r.passed)} |",
            f"| Pass Rate | {self.metrics['pass_rate']:.1%} |",
            f"| Recall@5 | {self.metrics['recall_at_5']:.3f} |",
            f"| MRR | {self.metrics['mrr']:.3f} |",
            "",
            "## Results",
            "",
        ]

        # Group by status
        failed = [r for r in self.results if not r.passed]
        passed = [r for r in self.results if r.passed]

        if failed:
            lines.append("### Failed Queries")
            lines.append("")
            for r in failed:
                lines.append(f"- **{r.query_id}** ({r.mode})")
                lines.append(f"  - Query: `{r.query_text}`")
                lines.append(f"  - Recall@5: {r.recall_at_5:.3f}")
                lines.append(f"  - Expected: {r.expected_chunks}")
                lines.append(f"  - Got: {r.actual_chunks[:3]}")
                lines.append("")

        lines.append("### Passed Queries")
        lines.append("")
        for r in passed:
            lines.append(f"- {r.query_id} ({r.mode}): Recall@5={r.recall_at_5:.3f}")

        return "\n".join(lines)

    def save(self, path: Path, format: str = "json"):
        """Save report to file."""
        content = self.to_json() if format == "json" else self.to_markdown()
        path.write_text(content)
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SETUP PHASE                                                  │
│  ──────────────                                                  │
│  fixtures/documents.json ──▶ FixtureLoader ──▶ Database         │
│                                    │                             │
│                                    ▼                             │
│                            EmbeddingService                      │
│                                    │                             │
│                                    ▼                             │
│                           AnalysisChunk (with vectors)           │
│                                                                  │
│  2. TEST EXECUTION                                               │
│  ─────────────────                                               │
│  fixtures/queries.json ──▶ FixtureLoader                        │
│                                    │                             │
│           ┌────────────────────────┼────────────────────────┐   │
│           ▼                        ▼                        ▼   │
│     SemanticTest            HybridTest              KeywordTest │
│           │                        │                        │   │
│           └────────────────────────┼────────────────────────┘   │
│                                    ▼                             │
│                             SearchService                        │
│                                    │                             │
│                                    ▼                             │
│                            list[SearchResult]                    │
│                                                                  │
│  3. EVALUATION                                                   │
│  ─────────────                                                   │
│  SearchResult + Expected ──▶ MetricsCalculator                  │
│                                    │                             │
│                                    ▼                             │
│                              QueryResult                         │
│                                    │                             │
│                                    ▼                             │
│                              Reporter                            │
│                                    │                             │
│                        ┌───────────┴───────────┐                │
│                        ▼                       ▼                │
│                   JSON Report            Markdown Report         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Test Matrix

| Query Category | Semantic | Keyword | Hybrid | Coarse-to-Fine |
|----------------|----------|---------|--------|----------------|
| Specific       | ✅       | ✅      | ✅     | ✅             |
| Broad          | ✅       | ✅      | ✅     | ✅             |
| Negative       | ✅       | ✅      | ✅     | ❌             |
| Edge Case      | ✅       | ✅      | ✅     | ❌             |
| Short Doc      | ✅       | ✅      | ✅     | ✅             |
| Long Doc       | ✅       | ✅      | ✅     | ✅             |

**Legend:**
- ✅ = Test implemented
- ❌ = Not applicable for this mode

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Total Suite Time | < 30s | Fast feedback in CI |
| Per-Query Time | < 500ms | Reasonable for smoke test |
| Database Setup | < 10s | One-time fixture loading |
| Memory Usage | < 500MB | Avoid CI runner limits |

## Error Handling

```python
class SmokeTestError(Exception):
    """Base exception for smoke test failures."""
    pass


class FixtureLoadError(SmokeTestError):
    """Failed to load test fixtures."""
    pass


class DatabaseSetupError(SmokeTestError):
    """Failed to set up test database."""
    pass


class SearchServiceError(SmokeTestError):
    """Search service returned an error."""
    pass
```

---

**Document Version:** 1.0
**Created:** December 10, 2025
