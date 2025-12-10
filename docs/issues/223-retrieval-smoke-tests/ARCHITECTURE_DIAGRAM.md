# Issue #223 - Retrieval Smoke Test Architecture

**Visual System Design for Offline Retrieval Testing**

---

## System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL SMOKE TEST SYSTEM                           │
│                         (<30s, Offline, Reproducible)                     │
└───────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────┐
                    │     FIXTURE REPOSITORY      │
                    │  (Version Controlled, Git)  │
                    └──────────────┬──────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
         ┌────────▼─────────┐             ┌────────▼─────────┐
         │   OFFLINE DATA   │             │   TEST QUERIES   │
         │  (133 Chunks +   │             │ (20 Queries +    │
         │   Embeddings)    │             │  Judgments)      │
         └────────┬─────────┘             └────────┬─────────┘
                  │                                 │
                  └────────────────┬────────────────┘
                                   │
                         ┌─────────▼──────────┐
                         │   CLI TEST RUNNER  │
                         │ (In-Memory Search) │
                         └─────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼─────────┐ ┌───────▼────────┐ ┌────────▼─────────┐
    │  SEMANTIC SEARCH  │ │ HYBRID SEARCH  │ │ COARSE-TO-FINE  │
    │   (Vector Only)   │ │ (70% Vec +     │ │  (Two-Stage)    │
    │                   │ │  30% Keyword)  │ │                 │
    └─────────┬─────────┘ └───────┬────────┘ └────────┬─────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                         ┌─────────▼──────────┐
                         │  METRICS EVALUATOR │
                         │ (Recall, MRR, NDCG)│
                         └─────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼─────────┐ ┌───────▼────────┐ ┌────────▼─────────┐
    │   TEXT OUTPUT     │ │  JSON OUTPUT   │ │ MARKDOWN OUTPUT  │
    │ (Human-Readable)  │ │ (CI Parsing)   │ │ (PR Comments)    │
    └───────────────────┘ └────────────────┘ └──────────────────┘
```

---

## Fixture Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FIXTURE GENERATION                              │
│                      (One-Time Setup / Updates)                         │
└─────────────────────────────────────────────────────────────────────────┘

   ┌──────────────────┐
   │   CURATED DOCS   │
   │   (15 Analyses)  │
   │                  │
   │ • 8 Long Docs    │
   │ • 5 Short Docs   │
   │ • 2 Edge Cases   │
   └────────┬─────────┘
            │
            ▼
   ┌─────────────────────────────┐
   │      CHUNKING SERVICE       │
   │  (Reuse Issue #221 Code)    │
   │                             │
   │  • Heading-aware splitting  │
   │  • Dynamic windows          │
   │  • Overlap (10-15%)         │
   │  • Coarse + Fine + Summary  │
   └────────┬────────────────────┘
            │
            ▼
   ┌─────────────────────────────┐
   │    DEDUPLICATION SERVICE    │
   │   (Shingle Hash Removal)    │
   │                             │
   │  • 133 unique chunks        │
   │  • 50 coarse                │
   │  • 75 fine                  │
   │  • 8 summary                │
   └────────┬────────────────────┘
            │
            ▼
   ┌─────────────────────────────┐
   │   EMBEDDING GENERATION      │
   │  (OpenAI API, One-Time)     │
   │                             │
   │  Model: text-embedding-     │
   │         3-small (768d)      │
   │  Cost: ~$0.10 total         │
   │  Time: ~2 minutes           │
   └────────┬────────────────────┘
            │
            ▼
   ┌─────────────────────────────┐
   │     FIXTURE PERSISTENCE     │
   │    (JSONL Files in Git)     │
   │                             │
   │  • analyses.jsonl   (~50KB) │
   │  • chunks.jsonl    (~200KB) │
   │  • embeddings.jsonl(~500KB) │
   │  • queries.jsonl    (~20KB) │
   │  • metadata.json     (~2KB) │
   └─────────────────────────────┘
```

---

## Test Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SMOKE TEST EXECUTION                               │
│                    (Every PR / Local Dev Run)                           │
└─────────────────────────────────────────────────────────────────────────┘

START: python -m scripts.test_retrieval --mode=all --verbose
  │
  ▼
┌──────────────────────────┐
│   LOAD FIXTURES (<2s)    │
│                          │
│  1. Read JSONL files     │
│  2. Build indices        │
│     - chunk_id → chunk   │
│     - chunk_id → emb     │
│  3. Validate integrity   │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│  FOR EACH QUERY (×20)    │
│                          │
│  q001: "How do React    │
│         Server Comps?"   │
└─────────┬────────────────┘
          │
          ├──────────────────────────────────────────────┐
          │                                              │
          ▼                                              ▼
┌───────────────────────┐                    ┌─────────────────────────┐
│   SEMANTIC SEARCH     │                    │   HYBRID SEARCH         │
│                       │                    │                         │
│ 1. Get query emb      │                    │ 1. Keyword matching     │
│ 2. Cosine sim all     │                    │    (TF overlap)         │
│ 3. Sort by score      │                    │ 2. Semantic scoring     │
│ 4. Return top-10      │                    │ 3. Blend (α=0.7)        │
│                       │                    │ 4. Return top-10        │
│ Time: ~0.5s           │                    │ Time: ~1s               │
└───────────┬───────────┘                    └──────────┬──────────────┘
            │                                           │
            └───────────────────┬───────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  COARSE-TO-FINE SEARCH  │
                    │                         │
                    │ 1. Coarse search (k=3)  │
                    │ 2. Extract sections     │
                    │ 3. Filter fine chunks   │
                    │ 4. Re-rank fine (k=10)  │
                    │                         │
                    │ Time: ~1.2s             │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   COMPUTE METRICS       │
                    │                         │
                    │ • Recall@5              │
                    │ • MRR                   │
                    │ • NDCG@10               │
                    │ • P@1                   │
                    │                         │
                    │ Time: ~0.1s             │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  THRESHOLD CHECK        │
                    │                         │
                    │ recall@5 ≥ 0.70?        │
                    │ mrr ≥ 0.60?             │
                    │ ndcg@10 ≥ 0.65?         │
                    │ p@1 ≥ 0.50?             │
                    │                         │
                    │ → ✅ PASS or ❌ FAIL    │
                    └────────────┬────────────┘
                                 │
                                 ▼
          ┌──────────────────────┴──────────────────────┐
          │                                             │
          ▼                                             ▼
┌───────────────────┐                        ┌──────────────────────┐
│  AGGREGATE STATS  │                        │  PER-QUERY DETAILS   │
│                   │                        │                      │
│ • Mean metrics    │                        │ • Top-5 results      │
│ • Min/max         │                        │ • Relevance scores   │
│ • Pass/fail count │                        │ • Snippets           │
└─────────┬─────────┘                        └──────────┬───────────┘
          │                                             │
          └──────────────────┬──────────────────────────┘
                             │
                             ▼
              ┌───────────────────────────────┐
              │     FORMAT OUTPUT             │
              │                               │
              │ --format=text   → Console     │
              │ --format=json   → CI parse    │
              │ --format=markdown → PR comment│
              └──────────────┬────────────────┘
                             │
                             ▼
                         END (Exit 0 or 1)
```

---

## Metric Computation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      METRIC CALCULATION FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

INPUT:
  results = [("chunk_001", 0.92), ("chunk_045", 0.88), ...]
  relevance = {"chunk_001": 3, "chunk_012": 2, "chunk_078": 1, ...}

┌──────────────────────────────────────────────────────────────────┐
│                         RECALL@5                                 │
│                                                                  │
│  Step 1: Extract top-5 chunk IDs                                │
│    top_5 = ["chunk_001", "chunk_045", "chunk_012", ...]         │
│                                                                  │
│  Step 2: Get all relevant chunk IDs (relevance > 0)             │
│    relevant = ["chunk_001", "chunk_012", "chunk_034", ...]      │
│                                                                  │
│  Step 3: Compute intersection                                   │
│    hits = set(top_5) ∩ set(relevant)                            │
│                                                                  │
│  Step 4: Calculate recall                                       │
│    recall@5 = |hits| / |relevant|                               │
│                                                                  │
│  Output: 0.80 (4/5 relevant chunks found)                       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                            MRR                                   │
│                                                                  │
│  Step 1: Iterate through results in order                       │
│    for rank, (chunk_id, score) in enumerate(results, start=1):  │
│                                                                  │
│  Step 2: Find first relevant result                             │
│    if relevance[chunk_id] > 0:                                  │
│      return 1.0 / rank                                          │
│                                                                  │
│  Step 3: Return reciprocal rank                                 │
│    mrr = 1.0 / 1 = 1.0 (first result relevant)                  │
│                                                                  │
│  Output: 1.0 (perfect ranking)                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                          NDCG@10                                 │
│                                                                  │
│  Step 1: Get relevance scores for top-10                        │
│    actual_rels = [3, 0, 2, 1, 2, 0, 1, 0, 0, 0]                 │
│                                                                  │
│  Step 2: Compute DCG (Discounted Cumulative Gain)               │
│    dcg = Σ (2^rel_i - 1) / log2(i + 1)                          │
│    dcg = 7/1 + 0/1.58 + 3/2 + 1/2.32 + ... = 10.09              │
│                                                                  │
│  Step 3: Compute Ideal DCG (best possible ranking)              │
│    ideal_rels = [3, 2, 2, 1, 1, 0, 0, 0, 0, 0]                  │
│    idcg = 7/1 + 3/1.58 + 3/2 + 1/2.32 + ... = 10.83             │
│                                                                  │
│  Step 4: Normalize                                              │
│    ndcg@10 = dcg / idcg = 10.09 / 10.83 = 0.93                  │
│                                                                  │
│  Output: 0.93 (excellent ranking quality)                       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                           P@1                                    │
│                                                                  │
│  Step 1: Get top-1 result                                       │
│    top_1 = "chunk_001"                                          │
│                                                                  │
│  Step 2: Check if relevant                                      │
│    relevance["chunk_001"] = 3 (highly relevant)                 │
│                                                                  │
│  Step 3: Return binary score                                    │
│    p@1 = 1.0 if relevant else 0.0                               │
│                                                                  │
│  Output: 1.0 (top result is relevant)                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## CI/CD Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

TRIGGER: Pull Request touching retrieval code
  │
  ├─ paths: backend/app/services/chunking/**
  ├─ paths: backend/app/workflows/utils/retrieval_routing.py
  ├─ paths: backend/app/db/repositories/chunk_repository.py
  └─ paths: backend/tests/fixtures/retrieval/**
  │
  ▼
┌────────────────────────────┐
│    CHECKOUT CODE (v4)      │
│                            │
│  uses: actions/checkout@v4 │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  SETUP PYTHON 3.13 (v5)    │
│                            │
│  with:                     │
│    cache: 'poetry'         │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│ CACHE FIXTURE EMBEDDINGS   │
│                            │
│ Key: metadata.json hash    │
│ Size: ~500KB               │
│ Hit Rate: >90%             │
│ Saves: ~10s per run        │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│   INSTALL DEPENDENCIES     │
│                            │
│  poetry install            │
│    --only main,test        │
│                            │
│ Time (cached): ~30s        │
│ Time (no cache): ~2min     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│   RUN SMOKE TESTS          │
│                            │
│  python -m scripts         │
│    .test_retrieval         │
│    --mode=all              │
│    --format=markdown       │
│    --output=results.md     │
│    --verbose               │
│                            │
│ Time: ~20s                 │
│ Exit: 0 (pass) or 1 (fail) │
└─────────────┬──────────────┘
              │
              ├──────────────────────┐
              │                      │
              ▼                      ▼
┌──────────────────────┐   ┌─────────────────────┐
│   UPLOAD ARTIFACT    │   │   POST PR COMMENT   │
│                      │   │                     │
│  name: smoke-test-   │   │  body: results.md   │
│        results       │   │                     │
│  retention: 30 days  │   │  includes:          │
│                      │   │  • Summary table    │
│  Always run (even    │   │  • Per-query stats  │
│  on failure)         │   │  • Status badge     │
└──────────────────────┘   └─────────────────────┘
              │
              ▼
┌────────────────────────────┐
│  FAIL IF TESTS FAILED      │
│                            │
│  exit 1 if smoke_tests     │
│         outcome == failure │
│                            │
│  → Blocks PR merge         │
└────────────────────────────┘
```

---

## Fixture Version Control Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FIXTURE VERSIONING                                 │
└─────────────────────────────────────────────────────────────────────────┘

metadata.json:
{
  "version": "1.2.0",
  "created_at": "2025-12-10T00:00:00Z",
  "updated_at": "2025-12-15T10:30:00Z",
  "model": "text-embedding-3-small",
  "model_version": "2024-11-01",
  "dimensions": 768,
  "total_analyses": 15,
  "total_chunks": 133,
  "changelog": [
    {
      "version": "1.2.0",
      "date": "2025-12-15",
      "changes": [
        "Updated 3 analyses with newer content",
        "Regenerated embeddings with new model version"
      ]
    },
    {
      "version": "1.1.0",
      "date": "2025-12-12",
      "changes": [
        "Added 2 edge case analyses",
        "Improved relevance judgments for 5 queries"
      ]
    },
    {
      "version": "1.0.0",
      "date": "2025-12-10",
      "changes": ["Initial fixture set"]
    }
  ]
}

┌──────────────────────────────────────────────────────────────┐
│                    WHEN TO UPDATE                            │
├──────────────────────────────────────────────────────────────┤
│ 1. Chunker Logic Changes (Issue #221 updates)               │
│    → Regenerate chunks.jsonl, embeddings.jsonl               │
│                                                              │
│ 2. Embedding Model Upgrade                                  │
│    → Regenerate embeddings.jsonl only                        │
│    → Bump model_version in metadata.json                     │
│                                                              │
│ 3. Query Set Expansion                                       │
│    → Add to queries.jsonl                                    │
│    → Bump minor version                                      │
│                                                              │
│ 4. Threshold Tuning                                          │
│    → Update metadata.json thresholds                         │
│    → No regeneration needed                                  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  REGENERATION WORKFLOW                       │
├──────────────────────────────────────────────────────────────┤
│ $ python -m scripts.generate_retrieval_fixtures \           │
│     --count=15 \                                             │
│     --output=backend/tests/fixtures/retrieval \              │
│     --model=text-embedding-3-small \                         │
│     --overwrite                                              │
│                                                              │
│ ⚠️  REVIEW CHANGES:                                          │
│ $ git diff backend/tests/fixtures/retrieval/                │
│                                                              │
│ ✅ COMMIT:                                                   │
│ $ git add backend/tests/fixtures/retrieval/                 │
│ $ git commit -m "chore: update retrieval fixtures to v1.2.0"│
└──────────────────────────────────────────────────────────────┘
```

---

## Performance Budget Breakdown

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE TARGETS                                  │
└─────────────────────────────────────────────────────────────────────────┘

TOTAL SMOKE TEST RUNTIME: <30 seconds

┌──────────────────────────────────────────┬───────────┬────────────┐
│ Component                                │ Time      │ % of Total │
├──────────────────────────────────────────┼───────────┼────────────┤
│ Fixture Loading                          │ <2s       │ 7%         │
│   - Read JSONL files (4 files)           │  1.2s     │            │
│   - Build indices (2 lookups)            │  0.5s     │            │
│   - Validate integrity                   │  0.3s     │            │
├──────────────────────────────────────────┼───────────┼────────────┤
│ Query Execution (20 queries)             │ <25s      │ 83%        │
│   - Semantic search (×20)                │  10s      │            │
│   - Hybrid search (×20)                  │  8s       │            │
│   - Coarse-to-fine search (×20)          │  7s       │            │
├──────────────────────────────────────────┼───────────┼────────────┤
│ Metrics Computation (20 × 4 metrics)     │ <2s       │ 7%         │
│   - Recall@5, MRR, NDCG@10, P@1          │  1.8s     │            │
├──────────────────────────────────────────┼───────────┼────────────┤
│ Output Formatting                        │ <1s       │ 3%         │
│   - Text/JSON/Markdown generation        │  0.8s     │            │
├──────────────────────────────────────────┼───────────┼────────────┤
│ TOTAL                                    │ <30s      │ 100%       │
└──────────────────────────────────────────┴───────────┴────────────┘

PER-QUERY BREAKDOWN:
  - Semantic search:      0.5s  (cosine sim over 133 vectors)
  - Hybrid search:        1.0s  (keyword + semantic)
  - Coarse-to-fine:       1.2s  (two-stage retrieval)
  - Metrics computation:  0.1s  (4 metrics)
  ---------------------------------------------------
  Total per query:        ~1.2s (average across modes)
```

---

**Last Updated:** December 10, 2025
**Maintained By:** Backend System Architect
