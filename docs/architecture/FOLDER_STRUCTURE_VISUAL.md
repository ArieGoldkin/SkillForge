# Folder Structure: Current vs Proposed (Visual Comparison)

## 🟡 CURRENT STATE (After Phase 1-6 Cleanup)

**Status**: Services cleaned ✅ | Schemas & Workflows remain ⚠️

```
app/
├── api/v1/                    ✅ API layer OK
│
├── schemas/                   ⚠️ Only API schemas
│   └── analyze.py
│
├── workflows/                 ❌ DEEP NESTING + SCATTERED
│   ├── agents/
│   │   ├── schemas/          ❌ Schemas 3 levels deep
│   │   │   └── implementation_planner.py
│   │   └── validation/       ❌ Validation 3 levels deep
│   │
│   ├── nodes/
│   │   └── agents/           ❌ Confusing: agents/ vs nodes/agents/
│   │       └── implementation_planner_node.py
│   │
│   ├── tasks/
│   │   ├── schemas/          ❌ Schemas 3 levels deep
│   │   │   └── core_synthesis.py
│   │   └── aggregation/      ❌ 3 levels deep
│   │
│   └── tutor/
│       ├── schemas/          ❌ Schemas 3 levels deep
│       ├── nodes/            ❌ 3 levels deep
│       └── tasks/            ❌ 3 levels deep
│
├── services/                  ✅ CLEANED: No duplicates
│   ├── embeddings/           ✅ Single source
│   │   ├── service.py
│   │   ├── deterministic.py
│   │   └── utils.py
│   ├── messaging/             ✅ Single source
│   │   └── sse_helpers.py
│   ├── persistence/           ✅ Single source
│   │   └── progress.py
│   ├── search/                ✅ Consolidated
│   │   └── coarse_to_fine.py  # Moved from retrieval/
│   └── ...
│
└── models/                    ✅ OK

REMAINING ISSUES:
⚠️ Schemas in 5 different locations (not yet consolidated)
⚠️ 3-4 levels of nesting (workflows still deep)
⚠️ No domain boundaries (still organized by technical layer)
⚠️ Hard to find related code (analysis code scattered)

FIXED:
✅ Duplicate files removed (Phase 1-2)
✅ Services organized (Phase 1-2)
✅ Imports updated (Phase 3)
```

---

## 🟢 PROPOSED STATE (Clean Architecture)

```
app/
├── api/v1/                    🌐 API Layer (thin, delegates)
│   └── analyze.py → domains.analysis.api
│
├── domains/                   🏗️ DOMAIN LAYER (business logic)
│   │
│   ├── analysis/              📊 Analysis Domain
│   │   ├── schemas/           ✅ ALL analysis schemas here
│   │   │   ├── api.py
│   │   │   ├── state.py
│   │   │   ├── agents/
│   │   │   │   └── implementation_planner.py
│   │   │   └── tasks/
│   │   │       └── synthesis.py
│   │   │
│   │   ├── workflows/         ✅ ALL analysis workflows
│   │   │   ├── agents/
│   │   │   ├── nodes/
│   │   │   └── tasks/
│   │   │
│   │   └── services/          ✅ Domain-specific services
│   │
│   ├── tutor/                 🎓 Tutor Domain
│   │   ├── schemas/           ✅ ALL tutor schemas
│   │   ├── workflows/         ✅ ALL tutor workflows
│   │   └── services/          ✅ Domain-specific services
│   │
│   └── evaluation/            📈 Evaluation Domain
│       ├── schemas/
│       ├── workflows/
│       └── services/
│
├── shared/                    🔧 SHARED INFRASTRUCTURE
│   ├── schemas/               ✅ Shared schemas
│   │   └── base.py
│   │
│   ├── services/              ✅ Shared services (single source)
│   │   ├── embeddings/        ✅ No duplicates!
│   │   │   └── service.py
│   │   ├── messaging/
│   │   │   └── sse_helpers.py  ✅ Single source!
│   │   └── persistence/
│   │       └── progress.py    ✅ Single source!
│   │
│   └── workflows/             ✅ Shared workflow utils
│       └── utils/
│
├── db/                        💾 Data Access
│   └── repositories/
│
└── models/                    🗄️ DB Models

BENEFITS:
✅ Schemas in 2 locations (domain + shared)
✅ Max 3 levels deep
✅ Zero duplicates
✅ Clear domain boundaries
✅ Easy to find code
```

---

## 📊 Side-by-Side Comparison

### Finding "Implementation Planner Schema"

**CURRENT:**
```
❌ workflows/agents/schemas/implementation_planner.py
   (3 levels deep, mixed with other agent code)
```

**PROPOSED:**
```
✅ domains/analysis/schemas/agents/implementation_planner.py
   (Clear: it's an analysis domain agent schema)
```

---

### Finding "Tutor State Schema"

**CURRENT:**
```
❌ workflows/tutor/schemas/state.py
   (3 levels deep, mixed with workflow code)
```

**PROPOSED:**
```
✅ domains/tutor/schemas/state.py
   (Clear: it's a tutor domain schema)
```

---

### Finding "SSE Helper"

**CURRENT:**
```
❌ services/sse_helpers.py OR services/messaging/sse_helpers.py?
   (Which one? Are they the same? 🤔)
```

**PROPOSED:**
```
✅ shared/services/messaging/sse_helpers.py
   (Single source of truth, clearly shared infrastructure)
```

---

### Finding "All Analysis Code"

**CURRENT:**
```
❌ Scattered across:
   - workflows/agents/
   - workflows/nodes/
   - workflows/tasks/
   - schemas/analyze.py
   - services/context/
   - services/embeddings/
   (Hard to find everything!)
```

**PROPOSED:**
```
✅ Everything in domains/analysis/
   - domains/analysis/schemas/
   - domains/analysis/workflows/
   - domains/analysis/services/
   (One place for everything!)
```

---

## 🎯 Key Principles

### 1. Domain-Driven Design
```
Each domain is self-contained:
domains/{domain}/
  ├── schemas/      (domain schemas)
  ├── workflows/    (domain workflows)
  └── services/     (domain services)
```

### 2. Shared Infrastructure
```
Cross-domain code goes in shared/:
shared/
  ├── schemas/      (base models, common types)
  ├── services/     (embeddings, extraction, messaging)
  └── workflows/    (shared utilities)
```

### 3. Clear Boundaries
```
API Layer    → Thin, delegates to domains
Domain Layer → Business logic, self-contained
Shared Layer → Infrastructure, reusable
Data Layer   → Repositories, models
```

---

## 📈 Metrics Comparison

| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| **Schema Locations** | 5 | 2 | 60% reduction |
| **Max Nesting Depth** | 4 levels | 3 levels | 25% reduction |
| **Duplicate Files** | 4+ | 0 | 100% elimination |
| **Domain Clarity** | ❌ Mixed | ✅ Clear | ∞ improvement |
| **Code Discovery** | ❌ Hard | ✅ Easy | ∞ improvement |

---

## 🚀 Migration Path

```
Phase 1: Create structure (non-breaking)
  → Create domains/ and shared/ directories
  → Copy files (keep old locations)

Phase 2: Update imports
  → Update all imports gradually
  → Run tests after each domain

Phase 3: Cleanup
  → Remove old files
  → Update docs
```

---

**Visual Guide**: Use this document for quick reference during refactoring.

