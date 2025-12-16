# 🎨 SkillForge Codebase Structure - ASCII Visualization

## 📊 CURRENT STATE (WITH ISSUES MARKED)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SKILLFORGE ROOT DIRECTORY                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

SkillForge/
│
├── 🔴 assets/                          [22 screenshots - should be gitignored]
│   └── Screenshot_*.png                ⚠️  Clutters root
│
├── 🔴 node_modules/                    [Shouldn't exist at root]
├── 🔴 package.json                     [Unclear purpose - frontend has own]
├── 🔴 PR_349_*.md                      [Should be in docs/issues/]
│
├── 📁 backend/                         [Python/FastAPI Backend]
│   │
│   ├── 🔴 docs/                        [DUPLICATES root docs/]
│   │   ├── evaluation/
│   │   └── issues/
│   │
│   ├── 🔴 tools/langsmith/             [Should be in app/services/ or app/core/]
│   │
│   ├── 📁 app/
│   │   │
│   │   ├── ✅ api/                     [Clean REST API - 12 files]
│   │   │   └── v1/
│   │   │
│   │   ├── ✅ core/                    [Core utilities - 14 files]
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── ...
│   │   │
│   │   ├── ✅ db/                      [Repository pattern - 9 files]
│   │   │   └── repositories/
│   │   │
│   │   ├── ✅ models/                  [SQLAlchemy models - 7 files]
│   │   │
│   │   ├── ✅ schemas/                 [Pydantic schemas - 5 files]
│   │   │
│   │   ├── 🟡 services/                [69 FILES - MIXED ORGANIZATION]
│   │   │   │
│   │   │   ├── 🔴 embeddings.py         [TOP-LEVEL - should be in embeddings/]
│   │   │   ├── 🔴 embeddings_utils.py  [TOP-LEVEL - should be in embeddings/]
│   │   │   ├── 🔴 embeddings_deterministic.py [TOP-LEVEL - should be in embeddings/]
│   │   │   ├── 🔴 event_broadcaster.py [TOP-LEVEL - should be in messaging/]
│   │   │   ├── 🔴 sse_helpers.py      [TOP-LEVEL - should be in messaging/]
│   │   │   ├── 🔴 progress_persistence.py [TOP-LEVEL - should be in persistence/]
│   │   │   ├── 🔴 markdown_sanitizer.py [TOP-LEVEL - should be in utils/]
│   │   │   ├── 🔴 langsmith_metrics.py [TOP-LEVEL - should be in metrics/]
│   │   │   │
│   │   │   ├── ✅ backpressure/        [4 files - well organized]
│   │   │   ├── ✅ chunking/            [4 files - well organized]
│   │   │   ├── ✅ cleanup/            [5 files + docs - well organized]
│   │   │   ├── ✅ context/            [7 files - well organized]
│   │   │   ├── ✅ extraction/         [5 files - well organized]
│   │   │   ├── ✅ mcp/                [6 files - well organized]
│   │   │   ├── ✅ memory/             [3 files - well organized]
│   │   │   ├── 🟡 metrics/            [3 files - could merge langsmith_metrics.py]
│   │   │   ├── ✅ pii/                [6 files - well organized]
│   │   │   ├── 🟡 retrieval/          [1 file - could merge into search/]
│   │   │   ├── ✅ search/             [5 files - well organized]
│   │   │   ├── ✅ tutor/              [4 files - well organized]
│   │   │   └── 🟡 validation/         [2 files - could move to core/]
│   │   │
│   │   ├── 🟡 workflows/               [120 FILES - COMPLEX NESTING]
│   │   │   │
│   │   │   ├── 🔴 agents/             [31 files - agent business logic]
│   │   │   │   ├── base.py
│   │   │   │   ├── tech_comparator.py
│   │   │   │   ├── security_auditor.py
│   │   │   │   ├── schemas/           [8 schema files]
│   │   │   │   └── validation/        [1 validation file]
│   │   │   │
│   │   │   ├── 🔴 nodes/              [17 files - LangGraph node wrappers]
│   │   │   │   ├── supervisor.py
│   │   │   │   ├── quality_gate_node.py
│   │   │   │   └── agents/            [8 agent node files]
│   │   │   │       ├── code_quality_critic_node.py
│   │   │   │       ├── dependency_mapper_node.py
│   │   │   │       └── ... (6 more)
│   │   │   │       ⚠️  DUPLICATION: Agent logic in agents/, nodes in nodes/agents/
│   │   │   │
│   │   │   ├── ✅ tasks/              [31 files - well organized]
│   │   │   │   ├── aggregation/       [9 files]
│   │   │   │   ├── schemas/           [3 files]
│   │   │   │   └── templates/         [2 files]
│   │   │   │
│   │   │   ├── ✅ tutor/              [25 files - well organized, separate workflow]
│   │   │   │   ├── nodes/             [10 files]
│   │   │   │   ├── tasks/             [3 files]
│   │   │   │   └── schemas/           [4 files]
│   │   │   │
│   │   │   ├── 🟡 evaluation/         [3 files - could be in app/evaluation/]
│   │   │   │
│   │   │   └── ✅ utils/              [6 files - well organized]
│   │   │
│   │   └── 🟡 evaluation/             [50+ FILES - LARGE MODULE]
│   │       ├── datasets/               [7 files]
│   │       ├── evaluators/            [5 files]
│   │       ├── ingestion/             [10 files]
│   │       ├── metrics/               [2 files]
│   │       ├── pipeline/              [3 files]
│   │       ├── schemas/               [3 files]
│   │       └── validation/            [5 files]
│   │       ⚠️  Could be its own package or clearly documented as internal tool
│   │
│   ├── 🔴 scripts/                    [32 FILES - NO CLEAR ORGANIZATION]
│   │   ├── regenerate_*.py            [6 similar files - could be subcommands]
│   │   ├── verify_*.py                 [3 similar files - could be subcommands]
│   │   ├── generate_*.py               [3 similar files - could be subcommands]
│   │   ├── load_*.py                   [2 similar files - could be subcommands]
│   │   └── ... (18 other scripts)      ⚠️  No grouping by purpose
│   │
│   ├── ✅ tests/                      [282 FILES - WELL ORGANIZED]
│   │   ├── unit/                       [185 files]
│   │   ├── integration/                [62 files]
│   │   ├── component/                 [5 files]
│   │   └── smoke/                     [25 files]
│   │
│   └── 🟡 data/                        [Golden dataset - could be in dedicated data/]
│
├── 📁 frontend/                        [React 19 Frontend]
│   │
│   └── src/
│       │
│       ├── ✅ features/                [189 FILES - EXCELLENT ORGANIZATION]
│       │   ├── analysis/               [Self-contained feature]
│       │   │   ├── components/
│       │   │   ├── hooks/
│       │   │   └── __tests__/
│       │   ├── artifact/               [Self-contained feature]
│       │   ├── home/                   [Self-contained feature]
│       │   ├── library/                [Self-contained feature]
│       │   ├── tutor/                  [Self-contained feature]
│       │   └── not-found/              [Self-contained feature]
│       │
│       ├── 🔴 store/                   [1 FILE - useAppStore.ts]
│       │   └── useAppStore.ts
│       │
│       ├── 🔴 stores/                  [5 FILES - DUPLICATION]
│       │   ├── sseStore.ts
│       │   ├── themeStore.ts
│       │   └── ...
│       │   ⚠️  ISSUE: Two directories for same concept (store vs stores)
│       │
│       ├── 🟡 router/                  [4 FILES - infrastructure]
│       │   ├── GlobalErrorComponent.tsx
│       │   ├── LazyRoute.tsx
│       │   └── ...
│       │
│       ├── 🟡 routes/                  [9 FILES - route definitions]
│       │   ├── analyze.$id.tsx
│       │   ├── artifact.$artifactId.tsx
│       │   └── ...
│       │   ⚠️  ISSUE: Unclear separation between router/ and routes/
│       │
│       ├── 🟡 shared/                  [MIXED CONCERNS]
│       │   ├── components/            ✅ UI components
│       │   ├── SkillLevelSelector.tsx  ⚠️  Should be in components/
│       │   └── SkillLevelSelector.css ⚠️  Should be with component
│       │
│       ├── ✅ hooks/                   [5 files - shared hooks]
│       ├── ✅ services/                [3 files - API services]
│       ├── ✅ types/                   [2 files - shared types]
│       └── ✅ design-system/           [7 files - design tokens]
│
├── 📁 docs/                            [182 FILES - NEEDS ORGANIZATION]
│   │
│   ├── 🔴 issues/                      [137 FOLDERS - NO STATUS TRACKING]
│   │   ├── 001-fastapi-structure/     [Old issues]
│   │   ├── 299-304-artifact-quality/  [Recent issues]
│   │   └── ... (135 more)               ⚠️  No status (open/closed/archived)
│   │
│   ├── 🟡 archive/                     [Only 1 file - underutilized]
│   ├── 🟡 reviews/                     [Empty directory]
│   │
│   ├── ✅ architecture/                [2 files - well organized]
│   ├── ✅ evaluation/                  [6 files - well organized]
│   ├── ✅ testing/                     [3 files - well organized]
│   ├── ✅ sprints/                     [2 files - well organized]
│   ├── 🟡 adr/                         [Only 1 ADR - should have more]
│   │
│   └── ✅ ROOT DOCS                    [15+ files - good high-level docs]
│       ├── ARCHITECTURE.md
│       ├── ROADMAP.md
│       └── CURRENT_STATUS.md
│
└── 📁 .claude/                          [WELL ORGANIZED - but large]
    ├── ✅ agents/                       [10 agent definitions]
    ├── ✅ skills/                      [18 skill modules with capabilities.json]
    ├── ✅ instructions/                [15 instruction files]
    ├── ✅ workflows/                    [3 pre-composed workflows]
    ├── 🟡 context/                      [Multiple context files - could consolidate]
    │   ├── session.json
    │   ├── shared-context.json
    │   └── quality_gate_review_evidence.json
    └── ✅ schemas/                      [JSON schemas for validation]
```

---

## 🎯 RECOMMENDED STRUCTURE (CLEAN)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RECOMMENDED REORGANIZATION                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

SkillForge/
│
├── 📁 backend/
│   │
│   ├── app/
│   │   ├── api/                        ✅ Keep as-is
│   │   ├── core/                       ✅ Keep as-is
│   │   ├── db/                         ✅ Keep as-is
│   │   ├── models/                     ✅ Keep as-is
│   │   ├── schemas/                    ✅ Keep as-is
│   │   │
│   │   ├── services/                   🔄 REORGANIZED
│   │   │   ├── embeddings/              🆕 [Group all embedding files]
│   │   │   │   ├── embeddings.py
│   │   │   │   ├── embeddings_utils.py
│   │   │   │   └── embeddings_deterministic.py
│   │   │   │
│   │   │   ├── messaging/              🆕 [SSE, events, broadcasting]
│   │   │   │   ├── event_broadcaster.py
│   │   │   │   └── sse_helpers.py
│   │   │   │
│   │   │   ├── persistence/            🆕 [Progress, state persistence]
│   │   │   │   └── progress_persistence.py
│   │   │   │
│   │   │   ├── utils/                  🆕 [Shared utilities]
│   │   │   │   └── markdown_sanitizer.py
│   │   │   │
│   │   │   ├── metrics/                🔄 [Merged langsmith_metrics.py]
│   │   │   │   ├── collectors.py
│   │   │   │   ├── service.py
│   │   │   │   └── langsmith_metrics.py
│   │   │   │
│   │   │   ├── search/                 🔄 [Merged retrieval/]
│   │   │   │   ├── search_service.py
│   │   │   │   ├── reranker.py
│   │   │   │   └── coarse_to_fine.py  [from retrieval/]
│   │   │   │
│   │   │   ├── backpressure/           ✅ Keep as-is
│   │   │   ├── chunking/               ✅ Keep as-is
│   │   │   ├── cleanup/                ✅ Keep as-is
│   │   │   ├── context/                ✅ Keep as-is
│   │   │   ├── extraction/             ✅ Keep as-is
│   │   │   ├── mcp/                    ✅ Keep as-is
│   │   │   ├── memory/                 ✅ Keep as-is
│   │   │   ├── pii/                    ✅ Keep as-is
│   │   │   └── tutor/                  ✅ Keep as-is
│   │   │
│   │   ├── workflows/                  🔄 CLARIFIED STRUCTURE
│   │   │   ├── agents/                 📝 [Business logic only]
│   │   │   │   ├── base.py
│   │   │   │   ├── tech_comparator.py
│   │   │   │   ├── schemas/
│   │   │   │   └── validation/
│   │   │   │
│   │   │   ├── nodes/                  📝 [LangGraph wrappers - FLATTENED]
│   │   │   │   ├── supervisor.py
│   │   │   │   ├── quality_gate_node.py
│   │   │   │   ├── agent_code_quality_critic.py  [from nodes/agents/]
│   │   │   │   ├── agent_dependency_mapper.py     [from nodes/agents/]
│   │   │   │   └── ... (flatten agent nodes)
│   │   │   │
│   │   │   ├── tasks/                  ✅ Keep as-is
│   │   │   ├── tutor/                  ✅ Keep as-is
│   │   │   └── utils/                  ✅ Keep as-is
│   │   │
│   │   └── evaluation/                 ✅ Keep as-is (or extract to package)
│   │
│   ├── scripts/                        🔄 GROUPED BY PURPOSE
│   │   ├── data/                       🆕 [Golden dataset scripts]
│   │   │   ├── backup_golden_dataset.py
│   │   │   ├── load_golden_dataset.py
│   │   │   └── verify_golden_dataset.py
│   │   │
│   │   ├── evaluation/                 🆕 [Evaluation scripts]
│   │   │   ├── run_evaluation.py
│   │   │   ├── generate_adversarial.py
│   │   │   └── generate_edge_cases.py
│   │   │
│   │   ├── validation/                 🆕 [Validation scripts]
│   │   │   ├── validate_app.py
│   │   │   └── validate_examples.py
│   │   │
│   │   └── utils/                      🆕 [General utilities]
│   │       └── cleanup.py
│   │
│   ├── tools/                          🔄 MOVED OR REMOVED
│   │   └── langsmith/                  → app/core/langsmith/ or app/services/metrics/
│   │
│   └── tests/                           ✅ Keep as-is
│
├── 📁 frontend/
│   └── src/
│       ├── features/                   ✅ Keep as-is (EXCELLENT)
│       │
│       ├── stores/                      🔄 MERGED (store/ → stores/)
│       │   ├── useAppStore.ts           [from store/]
│       │   ├── sseStore.ts
│       │   └── themeStore.ts
│       │
│       ├── router/                      📝 [Infrastructure - add README]
│       │   ├── GlobalErrorComponent.tsx
│       │   └── LazyRoute.tsx
│       │
│       ├── routes/                      📝 [Route definitions - add README]
│       │   ├── analyze.$id.tsx
│       │   └── artifact.$artifactId.tsx
│       │
│       ├── shared/                      🔄 REORGANIZED
│       │   └── components/              [All UI components]
│       │       ├── layout/
│       │       ├── navigation/
│       │       ├── ui/
│       │       └── SkillLevelSelector.tsx  [moved from root]
│       │
│       ├── hooks/                       ✅ Keep as-is
│       ├── services/                    ✅ Keep as-is
│       ├── types/                       ✅ Keep as-is
│       └── design-system/               ✅ Keep as-is
│
├── 📁 docs/
│   │
│   ├── issues/                         🔄 ORGANIZED BY STATUS
│   │   ├── active/                      🆕 [Open issues]
│   │   │   └── 299-304-artifact-quality/
│   │   │
│   │   ├── completed/                   🆕 [Closed issues]
│   │   │   └── 001-fastapi-structure/
│   │   │
│   │   └── archive/                      🆕 [Old/irrelevant issues]
│   │       └── 004-content-extraction-jina/
│   │
│   ├── backend/                         🆕 [Backend-specific docs]
│   │   └── [from backend/docs/]
│   │
│   ├── frontend/                        🆕 [Frontend-specific docs]
│   │
│   ├── architecture/                    ✅ Keep as-is
│   ├── evaluation/                      ✅ Keep as-is
│   ├── testing/                         ✅ Keep as-is
│   ├── sprints/                         ✅ Keep as-is
│   ├── adr/                             🔄 [Add more ADRs]
│   │
│   └── assets/                          🆕 [Screenshots, images]
│       └── [from root assets/]
│
└── 📁 .claude/                          ✅ Keep as-is (well organized)
```

---

## 🔴 CRITICAL ISSUES SUMMARY

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL: Store Duplication (Frontend)                              │
│     src/store/ (1 file) vs src/stores/ (5 files)                        │
│     → Consolidate into single src/stores/                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL: Agent Node Duplication (Backend)                          │
│     workflows/agents/ (business logic)                                  │
│     workflows/nodes/agents/ (LangGraph wrappers)                        │
│     → Add README explaining pattern OR flatten nodes/agents/            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL: Services Top-Level Files (Backend)                        │
│     8 top-level files mixed with subdirectories                        │
│     → Group into subdirectories (embeddings/, messaging/, etc.)         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL: Documentation Bloat                                       │
│     137 issue folders with no status tracking                           │
│     → Archive completed, add status metadata                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL: Scripts Disorganization (Backend)                          │
│     32 scripts with no clear grouping                                   │
│     → Group by purpose OR create CLI with subcommands                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ STRENGTHS TO PRESERVE

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ Frontend Feature Organization                                       │
│     Excellent feature-based structure (analysis/, artifact/, etc.)      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ Backend Repository Pattern                                          │
│     Clean separation of data access layer                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ Test Organization                                                   │
│     Clear unit/integration/component/smoke separation                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ Claude Agent System                                                 │
│     Well-organized with capabilities.json progressive loading           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ Workflow Separation                                                 │
│     Tutor workflow cleanly separated from analysis workflow            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**End of ASCII Visualization**

