# Issue #223 - Retrieval Smoke Test Suite Design

**Version:** 1.0
**Date:** December 10, 2025
**Status:** Design Complete
**Author:** Backend System Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Smoke Test Best Practices](#smoke-test-best-practices)
3. [Fixture Design Strategy](#fixture-design-strategy)
4. [CLI Script Architecture](#cli-script-architecture)
5. [Metrics & Evaluation](#metrics--evaluation)
6. [CI Integration](#ci-integration)
7. [Implementation Plan](#implementation-plan)
8. [Appendices](#appendices)

---

## Executive Summary

### Purpose
Create a lightweight, fast (<30s), offline retrieval smoke test suite that validates SkillForge's hierarchical chunking and coarse-to-fine retrieval system (Issue #221) without requiring external APIs or heavy computation.

### Goals
1. **Fast Feedback**: Detect retrieval regressions in CI/local dev (<30s total runtime)
2. **Offline Capable**: No OpenAI API calls; use pre-computed embeddings
3. **Representative Coverage**: Test semantic, hybrid, and coarse-to-fine modes
4. **Actionable Metrics**: Clear pass/fail thresholds with debugging context

### Key Design Decisions
- **Synthetic + Real Data**: Curated technical docs (10-15 analyses, 50-100 chunks)
- **Frozen Embeddings**: Pre-computed vectors checked into repo (~500KB)
- **Pass/Fail Thresholds**: Recall@5 ≥70%, MRR ≥0.6, NDCG@10 ≥0.65
- **CLI-First**: `python -m scripts.test_retrieval --mode=smoke --verbose`
- **CI Integration**: GitHub Actions with artifact caching

---

## Smoke Test Best Practices

### What Makes a Good Retrieval Smoke Test?

Based on research from Pinecone, Weaviate, and LangChain testing patterns:

#### 1. **Speed Over Comprehensiveness**
```
Smoke Tests (30s):
  - 10-15 analyses
  - 50-100 total chunks
  - Pre-computed embeddings
  - Frozen query set (15-20 queries)

vs.

Full Eval (5-10 min):
  - 100+ analyses
  - 1000+ chunks
  - Real-time embedding generation
  - Dynamic query generation
```

#### 2. **Reproducibility**
- **Frozen Embeddings**: No variance from model updates
- **Version Control**: Fixtures in Git (JSONL format)
- **Deterministic Metrics**: No probabilistic components
- **Idempotent**: Same input → same output every run

#### 3. **Representative Queries**
```python
Query Types to Cover:
1. Exact Match (keyword):      "React Server Components"
2. Semantic (paraphrase):       "async rendering in Next.js 15"
3. Multi-Concept (AND):         "PostgreSQL pgvector indexing"
4. Granularity (section):       "authentication middleware patterns"
5. Domain-Specific:             "LangGraph supervisor agent routing"
6. Negative (should fail):      "cat videos on TikTok"
```

#### 4. **Realistic Failure Modes**
Test against:
- **Chunking Boundaries**: Queries spanning multiple chunks
- **Deduplication**: Similar but distinct content
- **Granularity Mismatch**: Coarse query → fine results (or vice versa)
- **Stop Words**: Common terms ("how to", "best practices")

#### 5. **Clear Pass/Fail Criteria**
```python
# Industry Benchmarks (2025)
SMOKE_TEST_THRESHOLDS = {
    "recall@5": 0.70,      # 70% of relevant chunks in top 5
    "mrr": 0.60,            # Mean reciprocal rank ≥ 0.6
    "ndcg@10": 0.65,        # Normalized discounted cumulative gain
    "p@1": 0.50,            # Precision at 1 (first result correct)
}

# SkillForge Context: Lower than production (≥85%)
# but catches major regressions
```

---

## Fixture Design Strategy

### Architecture

```
backend/tests/fixtures/retrieval/
├── analyses.jsonl              # 10-15 curated technical analyses
├── chunks.jsonl                # 50-100 chunks (coarse + fine + summary)
├── embeddings.jsonl            # Pre-computed 768-dim vectors
├── queries.jsonl               # 15-20 test queries with relevance judgments
└── metadata.json               # Fixture stats and versioning
```

### Data Contract

#### `analyses.jsonl`
```json
{
  "analysis_id": "a001_react_server_components",
  "url": "https://react.dev/reference/rsc/server-components",
  "title": "React Server Components Deep Dive",
  "raw_content": "Full text extracted...",
  "content_type": "article",
  "language": "en",
  "doc_length": "long",
  "topics": ["React", "Server Components", "Next.js 15"]
}
```

#### `chunks.jsonl`
```json
{
  "chunk_id": "a001_coarse_intro",
  "analysis_id": "a001_react_server_components",
  "granularity": "coarse",
  "text": "Server Components are a new React feature...",
  "path": ["Introduction"],
  "section_title": "Introduction",
  "chunk_idx": 0,
  "chunk_total": 8,
  "hash": "sha256:abc123...",
  "content_type": "article",
  "language": "en",
  "snippet": "Server Components are a new React feature that allows..."
}
```

#### `embeddings.jsonl`
```json
{
  "chunk_id": "a001_coarse_intro",
  "embedding": [0.012, -0.034, 0.056, ...],  // 768 dims
  "model": "text-embedding-3-small",
  "model_version": "2024-11-01",
  "normalized": true
}
```

#### `queries.jsonl`
```json
{
  "query_id": "q001",
  "query_text": "How do server components work in React?",
  "query_type": "semantic",
  "expected_granularity": "coarse",
  "relevance_judgments": {
    "a001_coarse_intro": 3,        // Highly relevant
    "a001_fine_streaming": 2,      // Relevant
    "a001_summary": 1,             // Marginally relevant
    "a002_nextjs_cache": 0         // Not relevant
  },
  "min_recall@5": 0.8,             // Query-specific threshold
  "notes": "Tests basic semantic understanding of RSC concept"
}
```

### Fixture Selection Strategy

#### Synthetic vs Real Data

**Recommendation: 70% Real + 30% Synthetic**

```python
Real Data (70%):
  ✅ Authentic chunking boundaries
  ✅ Natural language variation
  ✅ Real-world edge cases
  ❌ Requires careful curation
  ❌ Larger storage (500KB+)

Synthetic Data (30%):
  ✅ Controlled test cases
  ✅ Known failure modes
  ✅ Minimal storage
  ❌ May miss real-world patterns
```

#### Concrete Fixture Plan (15 Analyses)

```python
Document Buckets (based on #221 config):

LONG Documents (8 analyses, >DOC_LENGTH_THRESHOLD):
  1. React Server Components (article)
  2. LangGraph Supervisor Pattern (tutorial)
  3. PostgreSQL PGVector Indexing (technical docs)
  4. FastAPI Async Patterns (API reference)
  5. Next.js 15 Streaming SSR (blog post)
  6. Hierarchical Chunking Paper (research)
  7. Vector Database Comparison (analysis)
  8. Embedding Model Evaluation (benchmark)

SHORT Documents (5 analyses):
  9. Quick Start Guide - Docker Compose
  10. Single-Concept Tutorial - JWT Auth
  11. Code Snippet Analysis - Python Decorator
  12. FAQ Page - LangChain Basics
  13. Release Notes - LangGraph v1.0

EDGE Cases (2 analyses):
  14. Markdown-Heavy Document (lots of code blocks)
  15. Multilingual Content (EN + code comments)
```

#### Coverage Matrix

```
┌─────────────────┬──────────┬──────────┬─────────┬───────────┐
│ Granularity     │ Coarse   │ Fine     │ Summary │ Total     │
├─────────────────┼──────────┼──────────┼─────────┼───────────┤
│ Long Docs (8)   │ 32       │ 48       │ 8       │ 88        │
│ Short Docs (5)  │ 10       │ 15       │ 0       │ 25        │
│ Edge Cases (2)  │ 8        │ 12       │ 0       │ 20        │
├─────────────────┼──────────┼──────────┼─────────┼───────────┤
│ Total Chunks    │ 50       │ 75       │ 8       │ 133       │
└─────────────────┴──────────┴──────────┴─────────┴───────────┘

Query Distribution (20 queries):
  - Semantic: 10 queries (paraphrase, conceptual)
  - Hybrid: 6 queries (keyword + semantic)
  - Granularity-specific: 4 queries (coarse vs fine)
```

#### Relevance Judgment Approach

```python
# Binary Relevance (SIMPLE)
relevance = {
  "chunk_id": 1 if relevant else 0
}

# Graded Relevance (RECOMMENDED)
relevance = {
  "chunk_id": {
    3: "Highly relevant (perfect answer)",
    2: "Relevant (partial answer)",
    1: "Marginally relevant (related context)",
    0: "Not relevant"
  }
}
```

**Strategy**: Use **graded relevance** for NDCG calculation; enables better ranking evaluation.

---

## CLI Script Architecture

### Interface Design

```bash
# Basic smoke test (default mode)
python -m scripts.test_retrieval

# Verbose mode with per-query breakdown
python -m scripts.test_retrieval --verbose

# Specific retrieval mode
python -m scripts.test_retrieval --mode=semantic
python -m scripts.test_retrieval --mode=hybrid
python -m scripts.test_retrieval --mode=coarse_to_fine

# JSON output for CI parsing
python -m scripts.test_retrieval --format=json --output=results.json

# Generate fixtures (one-time setup)
python -m scripts.generate_retrieval_fixtures --count=15

# Update embeddings (when model changes)
python -m scripts.update_fixture_embeddings --model=text-embedding-3-large
```

### Argument Specification

```python
# scripts/test_retrieval.py

import argparse

parser = argparse.ArgumentParser(
    description="Run retrieval smoke tests for SkillForge"
)

parser.add_argument(
    "--mode",
    choices=["semantic", "hybrid", "coarse_to_fine", "all"],
    default="all",
    help="Retrieval mode to test"
)

parser.add_argument(
    "--verbose", "-v",
    action="store_true",
    help="Show per-query results"
)

parser.add_argument(
    "--format",
    choices=["text", "json", "markdown"],
    default="text",
    help="Output format"
)

parser.add_argument(
    "--output", "-o",
    type=Path,
    help="Output file path (default: stdout)"
)

parser.add_argument(
    "--fixtures",
    type=Path,
    default=Path("backend/tests/fixtures/retrieval"),
    help="Path to fixture directory"
)

parser.add_argument(
    "--threshold-recall",
    type=float,
    default=0.70,
    help="Minimum Recall@5 threshold (default: 0.70)"
)

parser.add_argument(
    "--threshold-mrr",
    type=float,
    default=0.60,
    help="Minimum MRR threshold (default: 0.60)"
)

parser.add_argument(
    "--fail-fast",
    action="store_true",
    help="Exit on first query failure"
)

parser.add_argument(
    "--seed",
    type=int,
    default=42,
    help="Random seed for reproducibility"
)
```

### Script Structure

```python
# scripts/test_retrieval.py

from pathlib import Path
from typing import Dict, List
import json
import sys

from app.services.chunking.chunker import Chunker
from app.workflows.utils.retrieval_routing import coarse_to_fine_search
from app.db.repositories.chunk_repository import ChunkRepository

# ===== FIXTURE LOADING =====

def load_fixtures(fixtures_dir: Path):
    """Load all fixture files into memory."""
    analyses = load_jsonl(fixtures_dir / "analyses.jsonl")
    chunks = load_jsonl(fixtures_dir / "chunks.jsonl")
    embeddings = load_jsonl(fixtures_dir / "embeddings.jsonl")
    queries = load_jsonl(fixtures_dir / "queries.jsonl")
    metadata = load_json(fixtures_dir / "metadata.json")

    # Build lookup indices
    chunk_index = {c["chunk_id"]: c for c in chunks}
    embedding_index = {e["chunk_id"]: e for e in embeddings}

    return {
        "analyses": analyses,
        "chunks": chunks,
        "embeddings": embeddings,
        "queries": queries,
        "metadata": metadata,
        "indices": {
            "chunks": chunk_index,
            "embeddings": embedding_index,
        }
    }

# ===== IN-MEMORY SEARCH =====

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity (assumes normalized vectors)."""
    return sum(a * b for a, b in zip(vec_a, vec_b))

def semantic_search(
    query_embedding: List[float],
    chunk_embeddings: Dict[str, List[float]],
    k: int = 10
) -> List[tuple[str, float]]:
    """In-memory semantic search using pre-computed embeddings."""
    scores = [
        (chunk_id, cosine_similarity(query_embedding, emb))
        for chunk_id, emb in chunk_embeddings.items()
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:k]

def hybrid_search(
    query_text: str,
    query_embedding: List[float],
    chunks: Dict[str, dict],
    chunk_embeddings: Dict[str, List[float]],
    k: int = 10,
    alpha: float = 0.7  # Weight for semantic vs keyword
) -> List[tuple[str, float]]:
    """Hybrid search combining keyword + semantic."""
    # Keyword scores (simple TF overlap)
    query_terms = set(query_text.lower().split())
    keyword_scores = {}
    for chunk_id, chunk in chunks.items():
        chunk_terms = set(chunk["text"].lower().split())
        overlap = len(query_terms & chunk_terms)
        keyword_scores[chunk_id] = overlap / len(query_terms) if query_terms else 0.0

    # Semantic scores
    semantic_scores = dict(semantic_search(query_embedding, chunk_embeddings, k=len(chunks)))

    # Combine scores
    combined = [
        (chunk_id, alpha * semantic_scores.get(chunk_id, 0.0) + (1 - alpha) * keyword_scores.get(chunk_id, 0.0))
        for chunk_id in chunks.keys()
    ]
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:k]

def coarse_to_fine_search_mock(
    query_embedding: List[float],
    chunks: Dict[str, dict],
    chunk_embeddings: Dict[str, List[float]],
    k_coarse: int = 3,
    k_fine: int = 10
) -> List[tuple[str, float]]:
    """
    Mock coarse-to-fine search:
    1. Retrieve top-k coarse chunks
    2. Filter fine chunks to same sections
    3. Re-rank fine chunks
    """
    # Step 1: Coarse search
    coarse_chunks = {
        cid: emb for cid, emb in chunk_embeddings.items()
        if chunks[cid]["granularity"] == "coarse"
    }
    top_coarse = semantic_search(query_embedding, coarse_chunks, k=k_coarse)

    # Step 2: Get section paths from top coarse chunks
    top_sections = set()
    for chunk_id, _ in top_coarse:
        section_path = tuple(chunks[chunk_id]["path"])
        top_sections.add(section_path)

    # Step 3: Filter fine chunks to these sections
    fine_candidates = {
        cid: emb for cid, emb in chunk_embeddings.items()
        if chunks[cid]["granularity"] == "fine" and tuple(chunks[cid]["path"]) in top_sections
    }

    # Step 4: Re-rank fine chunks
    fine_results = semantic_search(query_embedding, fine_candidates, k=k_fine)

    return fine_results

# ===== METRICS =====

def compute_recall_at_k(
    results: List[tuple[str, float]],
    relevance: Dict[str, int],
    k: int = 5
) -> float:
    """Compute Recall@k: fraction of relevant items in top-k."""
    top_k = [chunk_id for chunk_id, _ in results[:k]]
    relevant = [cid for cid, rel in relevance.items() if rel > 0]

    if not relevant:
        return 0.0

    hits = len(set(top_k) & set(relevant))
    return hits / len(relevant)

def compute_mrr(
    results: List[tuple[str, float]],
    relevance: Dict[str, int]
) -> float:
    """Compute Mean Reciprocal Rank (MRR)."""
    for rank, (chunk_id, _) in enumerate(results, start=1):
        if relevance.get(chunk_id, 0) > 0:
            return 1.0 / rank
    return 0.0

def compute_ndcg_at_k(
    results: List[tuple[str, float]],
    relevance: Dict[str, int],
    k: int = 10
) -> float:
    """Compute Normalized Discounted Cumulative Gain (NDCG@k)."""
    import math

    def dcg(rels):
        return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(rels))

    # Actual DCG
    actual_rels = [relevance.get(chunk_id, 0) for chunk_id, _ in results[:k]]
    actual_dcg = dcg(actual_rels)

    # Ideal DCG
    ideal_rels = sorted(relevance.values(), reverse=True)[:k]
    ideal_dcg = dcg(ideal_rels)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg

def compute_precision_at_k(
    results: List[tuple[str, float]],
    relevance: Dict[str, int],
    k: int = 1
) -> float:
    """Compute Precision@k: fraction of top-k that are relevant."""
    top_k = [chunk_id for chunk_id, _ in results[:k]]
    relevant_in_k = sum(1 for cid in top_k if relevance.get(cid, 0) > 0)
    return relevant_in_k / k if k > 0 else 0.0

# ===== RUNNER =====

def run_smoke_tests(
    fixtures: dict,
    mode: str = "all",
    thresholds: dict = None,
    verbose: bool = False
) -> dict:
    """Run smoke tests and return results."""
    if thresholds is None:
        thresholds = {
            "recall@5": 0.70,
            "mrr": 0.60,
            "ndcg@10": 0.65,
            "p@1": 0.50,
        }

    results = {
        "metadata": fixtures["metadata"],
        "thresholds": thresholds,
        "queries": [],
        "summary": {},
        "passed": True,
    }

    chunk_index = fixtures["indices"]["chunks"]
    embedding_index = fixtures["indices"]["embeddings"]

    # Build embedding lookup
    chunk_embeddings = {
        cid: emb["embedding"]
        for cid, emb in embedding_index.items()
    }

    for query in fixtures["queries"]:
        query_id = query["query_id"]
        query_text = query["query_text"]
        query_type = query.get("query_type", "semantic")
        relevance = query["relevance_judgments"]

        # Get query embedding (in real implementation, this would be pre-computed)
        # For smoke tests, we'd have query embeddings in fixtures
        query_embedding = query.get("embedding", [0.0] * 768)  # Placeholder

        # Run search based on mode
        if mode in ["semantic", "all"]:
            search_results = semantic_search(query_embedding, chunk_embeddings, k=10)
        elif mode in ["hybrid", "all"]:
            search_results = hybrid_search(query_text, query_embedding, chunk_index, chunk_embeddings, k=10)
        elif mode in ["coarse_to_fine", "all"]:
            search_results = coarse_to_fine_search_mock(query_embedding, chunk_index, chunk_embeddings)
        else:
            search_results = []

        # Compute metrics
        metrics = {
            "recall@5": compute_recall_at_k(search_results, relevance, k=5),
            "mrr": compute_mrr(search_results, relevance),
            "ndcg@10": compute_ndcg_at_k(search_results, relevance, k=10),
            "p@1": compute_precision_at_k(search_results, relevance, k=1),
        }

        # Check thresholds
        passed = all(
            metrics[metric] >= threshold
            for metric, threshold in thresholds.items()
        )

        query_result = {
            "query_id": query_id,
            "query_text": query_text,
            "query_type": query_type,
            "metrics": metrics,
            "passed": passed,
            "results": [
                {
                    "chunk_id": cid,
                    "score": score,
                    "relevance": relevance.get(cid, 0),
                    "snippet": chunk_index[cid].get("snippet", "")[:100],
                }
                for cid, score in search_results[:5]
            ] if verbose else []
        }

        results["queries"].append(query_result)

        if not passed:
            results["passed"] = False

    # Compute summary statistics
    all_metrics = {
        metric: [q["metrics"][metric] for q in results["queries"]]
        for metric in thresholds.keys()
    }

    results["summary"] = {
        metric: {
            "mean": sum(values) / len(values) if values else 0.0,
            "min": min(values) if values else 0.0,
            "max": max(values) if values else 0.0,
            "threshold": thresholds[metric],
            "passed": sum(1 for v in values if v >= thresholds[metric]),
            "failed": sum(1 for v in values if v < thresholds[metric]),
        }
        for metric, values in all_metrics.items()
    }

    return results

# ===== OUTPUT FORMATTERS =====

def format_text_output(results: dict) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("RETRIEVAL SMOKE TEST RESULTS")
    lines.append("=" * 80)
    lines.append(f"Fixture Version: {results['metadata']['version']}")
    lines.append(f"Total Queries: {len(results['queries'])}")
    lines.append(f"Overall Status: {'✅ PASS' if results['passed'] else '❌ FAIL'}")
    lines.append("")

    lines.append("Summary Metrics:")
    lines.append("-" * 80)
    for metric, stats in results["summary"].items():
        status = "✅" if stats["passed"] == len(results["queries"]) else "⚠️"
        lines.append(
            f"{status} {metric.upper():12s} | "
            f"Mean: {stats['mean']:.3f} | "
            f"Threshold: {stats['threshold']:.2f} | "
            f"Passed: {stats['passed']}/{len(results['queries'])}"
        )

    lines.append("")
    lines.append("Per-Query Results:")
    lines.append("-" * 80)
    for query in results["queries"]:
        status = "✅" if query["passed"] else "❌"
        lines.append(f"{status} [{query['query_id']}] {query['query_text']}")
        for metric, value in query["metrics"].items():
            threshold = results["thresholds"][metric]
            marker = "✓" if value >= threshold else "✗"
            lines.append(f"    {marker} {metric}: {value:.3f} (threshold: {threshold:.2f})")
        lines.append("")

    return "\n".join(lines)

def format_json_output(results: dict) -> str:
    """Format results as JSON."""
    return json.dumps(results, indent=2)

def format_markdown_output(results: dict) -> str:
    """Format results as Markdown (for GitHub Actions summary)."""
    lines = []
    lines.append("# Retrieval Smoke Test Results")
    lines.append("")
    lines.append(f"**Status**: {'✅ PASS' if results['passed'] else '❌ FAIL'}")
    lines.append(f"**Fixture Version**: {results['metadata']['version']}")
    lines.append(f"**Total Queries**: {len(results['queries'])}")
    lines.append("")

    lines.append("## Summary Metrics")
    lines.append("")
    lines.append("| Metric | Mean | Threshold | Passed | Status |")
    lines.append("|--------|------|-----------|--------|--------|")
    for metric, stats in results["summary"].items():
        status = "✅" if stats["passed"] == len(results["queries"]) else "❌"
        lines.append(
            f"| {metric.upper()} | {stats['mean']:.3f} | {stats['threshold']:.2f} | "
            f"{stats['passed']}/{len(results['queries'])} | {status} |"
        )

    lines.append("")
    lines.append("## Query Results")
    lines.append("")
    for query in results["queries"]:
        status = "✅" if query["passed"] else "❌"
        lines.append(f"### {status} {query['query_id']}: {query['query_text']}")
        lines.append("")
        lines.append("| Metric | Score | Threshold | Status |")
        lines.append("|--------|-------|-----------|--------|")
        for metric, value in query["metrics"].items():
            threshold = results["thresholds"][metric]
            marker = "✅" if value >= threshold else "❌"
            lines.append(f"| {metric} | {value:.3f} | {threshold:.2f} | {marker} |")
        lines.append("")

    return "\n".join(lines)

# ===== MAIN =====

def main():
    parser = argparse.ArgumentParser()
    # ... (arguments from above)
    args = parser.parse_args()

    # Load fixtures
    fixtures = load_fixtures(args.fixtures)

    # Run tests
    thresholds = {
        "recall@5": args.threshold_recall,
        "mrr": args.threshold_mrr,
        "ndcg@10": 0.65,  # Add to args if needed
        "p@1": 0.50,
    }

    results = run_smoke_tests(
        fixtures,
        mode=args.mode,
        thresholds=thresholds,
        verbose=args.verbose
    )

    # Format output
    if args.format == "text":
        output = format_text_output(results)
    elif args.format == "json":
        output = format_json_output(results)
    elif args.format == "markdown":
        output = format_markdown_output(results)

    # Write output
    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    # Exit code
    sys.exit(0 if results["passed"] else 1)

if __name__ == "__main__":
    main()
```

---

## Metrics & Evaluation

### Core Metrics

#### 1. **Recall@k**
```python
Definition: Fraction of relevant chunks retrieved in top-k results

Recall@5 = |relevant ∩ top_5| / |relevant|

Interpretation:
  - 1.0 = Perfect (all relevant chunks in top-5)
  - 0.7 = Acceptable (70% of relevant chunks found)
  - <0.5 = Poor (missing majority of relevant content)

SkillForge Threshold: ≥0.70
Rationale: Users typically scan top 5 results
```

#### 2. **Mean Reciprocal Rank (MRR)**
```python
Definition: Average of reciprocal ranks of first relevant result

MRR = (1/n) Σ (1 / rank_first_relevant_i)

Example:
  Query 1: First relevant at rank 2 → RR = 0.5
  Query 2: First relevant at rank 1 → RR = 1.0
  Query 3: No relevant in top-10 → RR = 0.0
  MRR = (0.5 + 1.0 + 0.0) / 3 = 0.5

SkillForge Threshold: ≥0.60
Rationale: Ensures first relevant result typically in top 2-3
```

#### 3. **NDCG@10 (Normalized Discounted Cumulative Gain)**
```python
Definition: Ranking quality metric with position discount

DCG@k = Σ (2^rel_i - 1) / log2(i + 1)
NDCG@k = DCG@k / IDCG@k

Benefits:
  ✅ Accounts for graded relevance (3 > 2 > 1 > 0)
  ✅ Penalizes relevant results at lower ranks
  ✅ Industry standard (MSMARCO, TREC)

SkillForge Threshold: ≥0.65
Rationale: Good ranking quality without being overly strict
```

#### 4. **Precision@1**
```python
Definition: Is the top result relevant?

P@1 = 1 if top_result relevant else 0

SkillForge Threshold: ≥0.50
Rationale: At least half of queries should have perfect top result
```

### Pass/Fail Thresholds

```python
SMOKE_TEST_THRESHOLDS = {
    # Core metrics (all must pass)
    "recall@5": 0.70,       # 70% of relevant in top-5
    "mrr": 0.60,            # First relevant typically rank 1-2
    "ndcg@10": 0.65,        # Good ranking quality
    "p@1": 0.50,            # Half have perfect top result
}

# Per-query overrides allowed
QUERY_SPECIFIC_THRESHOLDS = {
    "q001_easy_exact_match": {"recall@5": 0.9, "p@1": 1.0},
    "q015_hard_semantic": {"recall@5": 0.5, "mrr": 0.4},
}

# Failure modes
FAIL_IF_ANY_METRIC_BELOW = 0.30  # Hard floor for any metric
FAIL_IF_ZERO_QUERIES = True      # Must have at least 1 query pass
```

### Debugging Metrics

```python
# Additional metrics for debugging (not pass/fail)
DEBUG_METRICS = {
    "avg_score_relevant": "Average similarity score for relevant chunks",
    "avg_score_irrelevant": "Average score for irrelevant chunks",
    "score_gap": "Difference between relevant and irrelevant scores",
    "granularity_distribution": "% of results by granularity (coarse/fine/summary)",
    "dedup_hit_rate": "% of queries affected by deduplication",
}
```

---

## CI Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/retrieval-smoke-tests.yml

name: Retrieval Smoke Tests

on:
  pull_request:
    paths:
      - 'backend/app/services/chunking/**'
      - 'backend/app/workflows/utils/retrieval_routing.py'
      - 'backend/app/db/repositories/chunk_repository.py'
      - 'backend/tests/fixtures/retrieval/**'
      - '.github/workflows/retrieval-smoke-tests.yml'
  push:
    branches:
      - main
      - dev

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'poetry'

      - name: Install dependencies
        run: |
          cd backend
          poetry install --only main,test --no-interaction

      - name: Cache fixture embeddings
        uses: actions/cache@v4
        with:
          path: backend/tests/fixtures/retrieval/embeddings.jsonl
          key: retrieval-fixtures-${{ hashFiles('backend/tests/fixtures/retrieval/metadata.json') }}
          restore-keys: |
            retrieval-fixtures-

      - name: Run smoke tests
        id: smoke_tests
        run: |
          cd backend
          poetry run python -m scripts.test_retrieval \
            --mode=all \
            --format=markdown \
            --output=smoke_test_results.md \
            --verbose
        continue-on-error: true

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-results
          path: backend/smoke_test_results.md
          retention-days: 30

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const markdown = fs.readFileSync('backend/smoke_test_results.md', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: markdown
            });

      - name: Fail workflow if tests failed
        if: steps.smoke_tests.outcome == 'failure'
        run: exit 1
```

### Caching Strategy

```yaml
# Cache fixture embeddings (largest file, rarely changes)
- name: Cache embeddings
  uses: actions/cache@v4
  with:
    path: backend/tests/fixtures/retrieval/embeddings.jsonl
    key: embeddings-${{ hashFiles('backend/tests/fixtures/retrieval/metadata.json') }}
    # ~500KB file, saves 5-10s per run

# Cache Python dependencies
- name: Cache Poetry dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pypoetry
    key: ${{ runner.os }}-poetry-${{ hashFiles('backend/poetry.lock') }}
```

### Performance Targets

```
CI Smoke Test Budget:
  - Fixture loading: <2s
  - Test execution: <15s (20 queries × <1s each)
  - Result formatting: <1s
  - Total: <20s

CI Caching Impact:
  - Without cache: ~30s (dependency install + test run)
  - With cache: ~20s (test run only)

Local Dev:
  - First run: ~25s (load fixtures + tests)
  - Subsequent: ~15s (fixtures cached in memory)
```

---

## Implementation Plan

### Phase 1: Fixture Generation (Week 1)

**Tasks:**
1. Create fixture directory structure
2. Curate 15 representative analyses
3. Generate chunks using existing chunker
4. Compute embeddings (one-time, using real API)
5. Create 20 test queries with relevance judgments
6. Validate fixture integrity

**Deliverables:**
- `backend/tests/fixtures/retrieval/` with all files
- `scripts/generate_retrieval_fixtures.py`
- Fixture documentation in `metadata.json`

**Acceptance Criteria:**
- Fixtures load in <2s
- Total size <1MB (embeddings compressed if needed)
- All chunks have valid embeddings
- Coverage matrix met (see above)

---

### Phase 2: CLI Script (Week 1-2)

**Tasks:**
1. Implement fixture loading utilities
2. Write in-memory search functions
3. Implement metrics computation
4. Create output formatters (text/JSON/markdown)
5. Add command-line argument parsing
6. Write unit tests for metrics functions

**Deliverables:**
- `scripts/test_retrieval.py`
- `scripts/test_retrieval_metrics.py` (metric utilities)
- Unit tests for metrics

**Acceptance Criteria:**
- Script runs in <30s locally
- All output formats working
- Metrics match reference implementations

---

### Phase 3: CI Integration (Week 2)

**Tasks:**
1. Create GitHub Actions workflow
2. Add caching for fixtures
3. Setup PR comment bot for results
4. Add workflow status badge to README
5. Test on example PR

**Deliverables:**
- `.github/workflows/retrieval-smoke-tests.yml`
- Updated `README.md` with badge

**Acceptance Criteria:**
- Workflow runs on every PR touching retrieval code
- Results posted as PR comment
- Workflow completes in <5 minutes
- Cache hit rate >90%

---

### Phase 4: Documentation & Maintenance (Week 2)

**Tasks:**
1. Write fixture update guide
2. Document threshold tuning process
3. Create troubleshooting guide
4. Setup fixture versioning strategy

**Deliverables:**
- `docs/issues/223-retrieval-smoke-tests/FIXTURE_GUIDE.md`
- `docs/issues/223-retrieval-smoke-tests/TROUBLESHOOTING.md`

**Acceptance Criteria:**
- Team can update fixtures without assistance
- Clear process for threshold adjustments
- Versioning strategy documented

---

## Appendices

### Appendix A: Fixture File Size Estimates

```
analyses.jsonl:     ~50KB  (15 analyses × 3-4KB each)
chunks.jsonl:       ~200KB (133 chunks × 1.5KB each)
embeddings.jsonl:   ~500KB (133 embeddings × 768 dims × 4 bytes)
queries.jsonl:      ~20KB  (20 queries with judgments)
metadata.json:      ~2KB
-----------------------------------
Total:              ~770KB (compressed: ~400KB with gzip)
```

### Appendix B: Metric Calculation Examples

```python
# Example: Query with graded relevance

query = "How do React Server Components work?"

results = [
    ("chunk_001", 0.92),  # Relevance: 3 (highly relevant)
    ("chunk_045", 0.88),  # Relevance: 0 (not relevant)
    ("chunk_012", 0.85),  # Relevance: 2 (relevant)
    ("chunk_078", 0.82),  # Relevance: 1 (marginally relevant)
    ("chunk_034", 0.80),  # Relevance: 2 (relevant)
]

relevance = {
    "chunk_001": 3,
    "chunk_012": 2,
    "chunk_034": 2,
    "chunk_078": 1,
    "chunk_045": 0,
}

# Recall@5
relevant_ids = ["chunk_001", "chunk_012", "chunk_034", "chunk_078"]
top_5_ids = ["chunk_001", "chunk_045", "chunk_012", "chunk_078", "chunk_034"]
recall@5 = len(set(relevant_ids) & set(top_5_ids)) / len(relevant_ids)
         = 4 / 4 = 1.0

# MRR
first_relevant_rank = 1 (chunk_001 at position 1)
mrr = 1.0 / 1 = 1.0

# NDCG@5
actual_rels = [3, 0, 2, 1, 2]
ideal_rels = [3, 2, 2, 1, 0]

dcg_actual = (2^3 - 1)/log2(2) + (2^0 - 1)/log2(3) + (2^2 - 1)/log2(4) + (2^1 - 1)/log2(5) + (2^2 - 1)/log2(6)
           = 7/1 + 0/1.58 + 3/2 + 1/2.32 + 3/2.58
           = 7.0 + 0.0 + 1.5 + 0.43 + 1.16
           = 10.09

dcg_ideal = (2^3 - 1)/log2(2) + (2^2 - 1)/log2(3) + (2^2 - 1)/log2(4) + (2^1 - 1)/log2(5) + (2^0 - 1)/log2(6)
          = 7/1 + 3/1.58 + 3/2 + 1/2.32 + 0/2.58
          = 7.0 + 1.90 + 1.5 + 0.43 + 0.0
          = 10.83

ndcg@5 = 10.09 / 10.83 = 0.93 ✅ (above threshold)

# P@1
top_1_relevant = relevance["chunk_001"] > 0
p@1 = 1.0 ✅
```

### Appendix C: Alternative Metrics Considered

```
MAP (Mean Average Precision):
  ✅ Pro: Standard in IR research
  ❌ Con: More complex than needed for smoke tests
  Decision: Use Recall@k instead (simpler, equally effective)

F1@k:
  ✅ Pro: Balances precision and recall
  ❌ Con: Threshold tuning harder
  Decision: Track separately but don't use for pass/fail

Hit Rate:
  ✅ Pro: Very simple (did we find ANY relevant?)
  ❌ Con: Too lenient (1 hit = pass)
  Decision: Too coarse for quality gate

Success@k:
  ✅ Pro: Domain-specific (conversational search)
  ❌ Con: Not applicable to SkillForge use case
  Decision: Not needed
```

### Appendix D: Research Sources

1. **Pinecone Evaluation Guide**: https://www.pinecone.io/learn/offline-evaluation/
2. **Weaviate Benchmarking**: https://weaviate.io/developers/weaviate/benchmarks
3. **MTEB (Massive Text Embedding Benchmark)**: https://github.com/embeddings-benchmark/mteb
4. **LangChain Retrieval QA Evaluation**: https://python.langchain.com/docs/guides/evaluation/
5. **TREC (Text REtrieval Conference)**: Standard IR evaluation methodology
6. **BEIR Benchmark**: Zero-shot retrieval evaluation framework

---

**End of Design Document**
