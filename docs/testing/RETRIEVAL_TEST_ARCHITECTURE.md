# Retrieval Smoke Test Architecture

**Purpose:** Visual architecture diagrams for the retrieval smoke test suite.  
**Companion Document:** [RETRIEVAL_SMOKE_TEST_STRATEGY.md](./RETRIEVAL_SMOKE_TEST_STRATEGY.md)

---

## Test Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL SMOKE TEST SUITE                           │
│                         (< 30 seconds, CI-friendly)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐      ┌───────────────────┐      ┌──────────────┐   │
│  │  FIXTURE LOADER   │─────▶│  TEST DATABASE    │◀─────│  TEST RUNNER │   │
│  │                   │      │                   │      │              │   │
│  │  - Corpus JSON    │      │  PostgreSQL       │      │  pytest      │   │
│  │  - Embeddings NPY │      │  + pgvector       │      │  32 tests    │   │
│  │  - Expected YAML  │      │  + tsvector       │      │              │   │
│  └───────────────────┘      └───────────────────┘      └──────────────┘   │
│           │                           │                        │           │
│           │                           │                        │           │
│           ▼                           ▼                        ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     TEST EXECUTION FLOW                             │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │                                                                     │  │
│  │  1. SETUP PHASE (5s)                                                │  │
│  │     - Create test database                                          │  │
│  │     - Load 100-150 chunks with frozen embeddings                    │  │
│  │     - Initialize search service                                     │  │
│  │                                                                     │  │
│  │  2. EXECUTION PHASE (20s)                                           │  │
│  │     ┌─────────────────┐   ┌─────────────────┐   ┌────────────────┐ │  │
│  │     │ SEMANTIC SEARCH │   │  HYBRID SEARCH  │   │ COARSE-TO-FINE │ │  │
│  │     │   10 tests      │   │    5 tests      │   │    5 tests     │ │  │
│  │     │   ~8s           │   │    ~6s          │   │    ~6s         │ │  │
│  │     └─────────────────┘   └─────────────────┘   └────────────────┘ │  │
│  │              │                     │                      │          │  │
│  │              └─────────────────────┴──────────────────────┘          │  │
│  │                                   │                                  │  │
│  │     ┌────────────────────────────────────────────────────────────┐  │  │
│  │     │               EDGE CASES & PERFORMANCE                     │  │
│  │     │                     12 tests, ~6s                          │  │
│  │     └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  3. TEARDOWN PHASE (< 1s)                                           │  │
│  │     - Truncate tables                                               │  │
│  │     - Close connections                                             │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         OUTPUT ARTIFACTS                            │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │  - JUnit XML report (test-results/smoke-tests.xml)                  │  │
│  │  - Coverage report (htmlcov/)                                       │  │
│  │  - Performance metrics (latency.json)                               │  │
│  │  - Failure screenshots (if applicable)                              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Test Database Isolation Strategies

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                   TEST ISOLATION COMPARISON                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  STRATEGY 1: IN-MEMORY SQLITE                                              ║
║  ═════════════════════════                                                 ║
║                                                                            ║
║    ┌──────────────┐         ┌──────────────┐                              ║
║    │  Test Runner │────────▶│  SQLite RAM  │                              ║
║    └──────────────┘         └──────────────┘                              ║
║                                                                            ║
║    Speed: ⚡⚡⚡ < 1s          Limitations: ❌ No pgvector, no tsvector    ║
║    Use For: Query validation, snippet generation, error handling          ║
║                                                                            ║
║────────────────────────────────────────────────────────────────────────────║
║                                                                            ║
║  STRATEGY 2: POSTGRESQL CONTAINER (Local Development)                     ║
║  ══════════════════════════════════════════════                           ║
║                                                                            ║
║    ┌──────────────┐         ┌──────────────────┐                          ║
║    │  Test Runner │────────▶│  Docker          │                          ║
║    └──────────────┘         │  pgvector:pg16   │                          ║
║                             │  + extensions    │                          ║
║                             └──────────────────┘                          ║
║                                      │                                     ║
║                                      ▼                                     ║
║                             ┌──────────────────┐                          ║
║                             │  Ephemeral DB    │                          ║
║                             │  Auto-cleanup    │                          ║
║                             └──────────────────┘                          ║
║                                                                            ║
║    Speed: ⚡⚡ 5-10s          Realism: ✅ Full pgvector + tsvector         ║
║    Use For: Integration tests, vector search, hybrid search, coarse-fine  ║
║                                                                            ║
║────────────────────────────────────────────────────────────────────────────║
║                                                                            ║
║  STRATEGY 3: DEDICATED TEST DATABASE (CI/CD)                              ║
║  ══════════════════════════════════════════                               ║
║                                                                            ║
║    ┌──────────────┐         ┌──────────────────┐                          ║
║    │  GitHub      │────────▶│  GitHub Actions  │                          ║
║    │  Workflow    │         │  Service         │                          ║
║    └──────────────┘         │  postgres:pg16   │                          ║
║                             └──────────────────┘                          ║
║                                      │                                     ║
║                                      ▼                                     ║
║                             ┌──────────────────┐                          ║
║                             │  Test DB         │                          ║
║                             │  Fixtures loaded │                          ║
║                             │  Per workflow    │                          ║
║                             └──────────────────┘                          ║
║                                                                            ║
║    Speed: ⚡⚡⚡ < 3s          CI-Friendly: ✅ Yes (no Docker overhead)    ║
║    Use For: All smoke tests in CI pipeline                                ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Test Category Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TEST CATEGORY BREAKDOWN                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. POSITIVE TESTS (Expected Matches)                                       │
│  ═════════════════════════════════                                          │
│                                                                             │
│     Query: "OAuth2 authentication"                                          │
│        │                                                                    │
│        ▼                                                                    │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  SEMANTIC SEARCH                                           │         │
│     │  ─────────────────                                         │         │
│     │  1. Generate embedding (1536 dimensions)                   │         │
│     │  2. Cosine similarity: <=> operator                        │         │
│     │  3. Score threshold: >= 0.85                               │         │
│     └────────────────────────────────────────────────────────────┘         │
│                       │                                                     │
│                       ▼                                                     │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Expected Result:                                          │         │
│     │  - chunk_id: "oauth2_tutorial_intro_coarse"                │         │
│     │  - min_score: 0.85                                         │         │
│     │  - max_rank: 3 (must be in top 3)                          │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  2. NEGATIVE TESTS (Expected Non-Matches)                                   │
│  ═══════════════════════════════════════                                    │
│                                                                             │
│     Query: "OAuth2"                                                         │
│        │                                                                    │
│        ▼                                                                    │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Should NOT match:                                         │         │
│     │  - chunk_id: "css_styling_guide_intro"                     │         │
│     │  - max_score: 0.40 (should score below this)               │         │
│     └────────────────────────────────────────────────────────────┘         │
│                       │                                                     │
│                       ▼                                                     │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Validation:                                               │         │
│     │  - If chunk found in results, score < 0.40                 │         │
│     │  - Test passes if chunk NOT in top 10                      │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  3. HYBRID SEARCH (RRF Fusion)                                              │
│  ═════════════════════════                                                  │
│                                                                             │
│     Query: "FastAPI OAuth2"                                                 │
│        │                                                                    │
│        ├──────────────────┬──────────────────┐                             │
│        ▼                  ▼                  ▼                             │
│     ┌────────────┐   ┌────────────┐   ┌────────────┐                      │
│     │  SEMANTIC  │   │  KEYWORD   │   │    RRF     │                      │
│     │  (vector)  │   │ (tsvector) │   │   FUSION   │                      │
│     └────────────┘   └────────────┘   └────────────┘                      │
│          │                 │                 │                             │
│          └─────────────────┴─────────────────┘                             │
│                           │                                                │
│                           ▼                                                │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Combined Score (RRF):                                     │         │
│     │  score = 1/(60 + semantic_rank) + 1/(60 + keyword_rank)   │         │
│     │                                                            │         │
│     │  Expected: min_score >= 0.90 (keyword boost)              │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  4. COARSE-TO-FINE RETRIEVAL (Two-Stage)                                    │
│  ═══════════════════════════════════════                                    │
│                                                                             │
│     Query: "LangGraph state management"                                     │
│        │                                                                    │
│        ▼                                                                    │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  STAGE 1: COARSE SEARCH                                    │         │
│     │  ──────────────────────                                    │         │
│     │  - Filter: granularity = "coarse"                          │         │
│     │  - Semantic search on section-level chunks                 │         │
│     │  - Returns: Top 5 sections                                 │         │
│     │                                                            │         │
│     │  Results:                                                  │         │
│     │    1. "LangGraph Architecture" (score: 0.89)               │         │
│     │    2. "Agent Design Patterns" (score: 0.82)                │         │
│     │    3. "State Management" (score: 0.78)                     │         │
│     │    4. ... (2 more sections)                                │         │
│     └────────────────────────────────────────────────────────────┘         │
│                       │                                                     │
│                       ▼                                                     │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  STAGE 2: FINE SEARCH (Constrained)                       │         │
│     │  ──────────────────────────────                           │         │
│     │  - Filter: granularity = "fine"                            │         │
│     │  - Filter: path starts with top 5 coarse sections          │         │
│     │  - Semantic search on paragraph-level chunks               │         │
│     │  - Returns: Top 5 paragraphs within top 5 sections         │         │
│     │                                                            │         │
│     │  Results:                                                  │         │
│     │    1. "LangGraph Architecture > State Design" (0.93)       │         │
│     │    2. "Agent Design Patterns > State Nodes" (0.87)         │         │
│     │    3. ... (3 more paragraphs)                              │         │
│     └────────────────────────────────────────────────────────────┘         │
│                       │                                                     │
│                       ▼                                                     │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Validation:                                               │         │
│     │  - All fine results have path starting with coarse section │         │
│     │  - 3-10 fine results returned                              │         │
│     │  - No results from unrelated sections                      │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Fixture Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FIXTURE GENERATION & LOADING                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ONE-TIME SETUP (Commit to Repo)                                            │
│  ════════════════════════════                                               │
│                                                                             │
│     ┌──────────────────────┐                                                │
│     │  Raw Test Documents  │                                                │
│     │  - 10-15 markdown    │                                                │
│     │  - Technical content │                                                │
│     └──────────────────────┘                                                │
│              │                                                              │
│              ▼                                                              │
│     ┌─────────────────────────────────────┐                                 │
│     │  scripts/generate_test_embeddings.py │                                │
│     │  ────────────────────────────────────│                                │
│     │  1. Chunk documents (coarse + fine)  │                                │
│     │  2. Generate embeddings via OpenAI   │                                │
│     │  3. Save as .npy files               │                                │
│     └─────────────────────────────────────┘                                 │
│              │                                                              │
│              ▼                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  tests/fixtures/                                           │         │
│     │  ────────────────                                          │         │
│     │  retrieval_corpus.json (100-150 chunks)                    │         │
│     │  expected_results.yaml (30 query specs)                    │         │
│     │  embeddings/                                               │         │
│     │    ├── oauth2_tutorial_intro_coarse.npy                    │         │
│     │    ├── fastapi_docs_auth_fine_1.npy                        │         │
│     │    └── ... (100-150 .npy files)                            │         │
│     │  embeddings_manifest.json (chunk_id → file mapping)        │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  TEST EXECUTION (Every CI Run)                                              │
│  ══════════════════════════                                                 │
│                                                                             │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  tests/conftest.py                                         │         │
│     │  ──────────────────                                        │         │
│     │  @pytest.fixture(scope="session")                          │         │
│     │  async def setup_test_db():                                │         │
│     └────────────────────────────────────────────────────────────┘         │
│              │                                                              │
│              ▼                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  1. Create test database (PostgreSQL + pgvector)           │         │
│     │  2. Load retrieval_corpus.json                             │         │
│     │  3. For each chunk:                                        │         │
│     │     a. Load frozen embedding from .npy file                │         │
│     │     b. Insert into analysis_chunks table                   │         │
│     │  4. Create indexes (HNSW for vector, GIN for tsvector)     │         │
│     └────────────────────────────────────────────────────────────┘         │
│              │                                                              │
│              ▼                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Database State:                                           │         │
│     │  ──────────────                                            │         │
│     │  analysis_chunks (100-150 rows)                            │         │
│     │    - id, analysis_id, content, vector, granularity, ...    │         │
│     │                                                            │         │
│     │  Indexes:                                                  │         │
│     │    - HNSW on vector (m=16, ef_construction=64)             │         │
│     │    - GIN on search_vector (for full-text)                  │         │
│     │    - B-tree on granularity, analysis_id                    │         │
│     └────────────────────────────────────────────────────────────┘         │
│              │                                                              │
│              ▼                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Test Execution:                                           │         │
│     │  - 32 test cases run against populated DB                  │         │
│     │  - No external API calls (frozen embeddings)               │         │
│     │  - Each test validates expected vs actual results          │         │
│     └────────────────────────────────────────────────────────────┘         │
│              │                                                              │
│              ▼                                                              │
│     ┌────────────────────────────────────────────────────────────┐         │
│     │  Teardown:                                                 │         │
│     │  - TRUNCATE analysis_chunks CASCADE                        │         │
│     │  - Close DB connections                                    │         │
│     │  - Generate test reports                                   │         │
│     └────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Assertion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CUSTOM ASSERTION HELPERS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. assert_score_near(actual, expected, tolerance, direction)               │
│  ═══════════════════════════════════════════════════════                    │
│                                                                             │
│     Input:                                                                  │
│       actual_score = 0.87                                                   │
│       expected_score = 0.85                                                 │
│       tolerance = 0.02                                                      │
│       direction = ">="                                                      │
│                                                                             │
│     Logic:                                                                  │
│       if direction == ">=":                                                 │
│           assert actual >= expected - tolerance                             │
│           assert 0.87 >= 0.85 - 0.02  # 0.87 >= 0.83 ✅                     │
│                                                                             │
│     Why: Floating-point variance in cosine similarity requires tolerance    │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  2. assert_in_top_k(results, chunk_id, k)                                   │
│  ═══════════════════════════════════                                        │
│                                                                             │
│     Input:                                                                  │
│       results = [SearchResult(...), SearchResult(...), ...]                 │
│       chunk_id = "oauth2_tutorial_intro_coarse"                             │
│       k = 3                                                                 │
│                                                                             │
│     Logic:                                                                  │
│       top_k_ids = [r.chunk_id for r in results[:k]]                         │
│       assert chunk_id in top_k_ids                                          │
│                                                                             │
│     Why: More resilient than exact rank (handles score ties)                │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  3. assert_snippet_contains(result, query_term)                             │
│  ═══════════════════════════════════════════                                │
│                                                                             │
│     Input:                                                                  │
│       result.snippet = "...provides <mark>OAuth2</mark> support..."         │
│       query_term = "OAuth2"                                                 │
│                                                                             │
│     Logic:                                                                  │
│       assert f"<mark>{query_term}</mark>" in result.snippet                 │
│                                                                             │
│     Why: Validates snippet generation and highlighting work correctly       │
│                                                                             │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  4. assert_metadata_field(result, field, expected_value)                    │
│  ══════════════════════════════════════════════════                         │
│                                                                             │
│     Input:                                                                  │
│       result.metadata.granularity = "coarse"                                │
│       field = "granularity"                                                 │
│       expected_value = "coarse"                                             │
│                                                                             │
│     Logic:                                                                  │
│       actual_value = getattr(result.metadata, field)                        │
│       assert actual_value == expected_value                                 │
│                                                                             │
│     Why: Validates coarse-to-fine retrieval returns correct granularity     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CI/CD Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   GITHUB ACTIONS WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Trigger: PR to main/dev with changes to search/* or tests/smoke/*          │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 1: Setup Environment                                            │  │
│  │  ─────────────────────────                                            │  │
│  │  - Checkout code                                                      │  │
│  │  - Python 3.13 + Poetry                                               │  │
│  │  - PostgreSQL service (pgvector:pg16)                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                 │                                                            │
│                 ▼                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 2: Install Dependencies                                         │  │
│  │  ────────────────────────                                             │  │
│  │  cd backend && poetry install --with dev                              │  │
│  │  Installs: pytest, asyncpg, pgvector, etc.                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                 │                                                            │
│                 ▼                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 3: Run Smoke Tests                                              │  │
│  │  ────────────────────                                                 │  │
│  │  poetry run pytest tests/smoke/ \                                     │  │
│  │    --verbose --tb=short --maxfail=3 --timeout=300                     │  │
│  │                                                                       │  │
│  │  Environment:                                                         │  │
│  │    DATABASE_URL=postgresql+asyncpg://test:pass@localhost/test        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                 │                                                            │
│                 ├──────────────┬──────────────┬──────────────┐              │
│                 ▼              ▼              ▼              ▼              │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  SEMANTIC (10)  │  │ HYBRID (5)  │  │  C2F (5)    │  │  EDGE (12)   │  │
│  │  8s             │  │ 6s          │  │  6s         │  │  6s          │  │
│  └─────────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │
│         │                    │                 │                │           │
│         └────────────────────┴─────────────────┴────────────────┘           │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 4: Generate Reports                                             │  │
│  │  ─────────────────────                                                │  │
│  │  - JUnit XML (test-results/smoke-tests.xml)                           │  │
│  │  - Coverage HTML (htmlcov/)                                           │  │
│  │  - Performance JSON (latency.json)                                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                 │                                                            │
│                 ▼                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 5: Upload Artifacts                                             │  │
│  │  ────────────────────                                                 │  │
│  │  if: always()                                                         │  │
│  │  uses: actions/upload-artifact@v4                                     │  │
│  │  with: name=smoke-test-report, path=backend/test-results/             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                 │                                                            │
│                 ▼                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Result: ✅ PASS or ❌ FAIL                                            │  │
│  │  ──────────────────────                                               │  │
│  │  - Pass: PR can be merged                                             │  │
│  │  - Fail: PR blocked, review test failures                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Performance Monitoring

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   LATENCY THRESHOLDS & MONITORING                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Search Mode          │  Target (p95)  │  Baseline  │  Alert Threshold     │
│  ────────────────────────────────────────────────────────────────────────  │
│  Semantic Search      │   < 100ms      │   80ms     │   > 120ms (FAIL)     │
│  Hybrid Search        │   < 150ms      │  130ms     │   > 180ms (FAIL)     │
│  Coarse-to-Fine       │   < 200ms      │  170ms     │   > 240ms (FAIL)     │
│  Keyword-Only         │   < 50ms       │   35ms     │   > 60ms (WARN)      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Performance Test Flow:                                               │  │
│  │  ──────────────────────                                               │  │
│  │                                                                       │  │
│  │  1. Run query 10 times                                                │  │
│  │  2. Measure latency for each run                                      │  │
│  │  3. Calculate p50, p95, p99                                           │  │
│  │  4. Assert p95 < threshold                                            │  │
│  │  5. Record to latency.json                                            │  │
│  │                                                                       │  │
│  │  Example:                                                             │  │
│  │    semantic_search("OAuth2 auth") x 10                                │  │
│  │    Results: [78ms, 82ms, 79ms, 81ms, 83ms, 80ms, 84ms, 79ms, 81ms]   │  │
│  │    p50: 81ms ✅                                                        │  │
│  │    p95: 84ms ✅ (< 100ms threshold)                                    │  │
│  │    p99: 84ms ✅                                                        │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Latency Breakdown (Semantic Search):                                 │  │
│  │  ──────────────────────────────────                                   │  │
│  │                                                                       │  │
│  │  Total: 81ms                                                          │  │
│  │    ├─ Embedding Generation: 20ms (25%)                                │  │
│  │    ├─ Vector Search (HNSW): 45ms (55%)                                │  │
│  │    ├─ Metadata Hydration: 10ms (12%)                                  │  │
│  │    └─ Snippet Generation: 6ms (8%)                                    │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

This architecture document provides visual representations of:

1. **Test Flow Architecture** - Overall smoke test suite execution
2. **Test Isolation Strategies** - Three approaches (SQLite, Container, Dedicated DB)
3. **Test Category Architecture** - Positive, negative, hybrid, coarse-to-fine
4. **Fixture Data Flow** - One-time generation vs test execution
5. **Assertion Flow** - Custom helper functions and their logic
6. **CI/CD Integration** - GitHub Actions workflow breakdown
7. **Performance Monitoring** - Latency thresholds and measurement approach

For detailed implementation guidance, see [RETRIEVAL_SMOKE_TEST_STRATEGY.md](./RETRIEVAL_SMOKE_TEST_STRATEGY.md).
