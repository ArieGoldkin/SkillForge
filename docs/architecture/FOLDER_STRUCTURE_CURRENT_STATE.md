# Current Folder Structure (After Phase 1-6 Cleanup)

**Status**: Services cleaned ✅ | Schemas & Workflows remain ⚠️

---

## ✅ What's Been Fixed

### Services Layer (Clean)
```
app/services/
├── embeddings/              ✅ Single source (was: embeddings.py + embeddings/)
│   ├── service.py
│   ├── deterministic.py
│   └── utils.py
│
├── messaging/               ✅ Single source (was: sse_helpers.py + messaging/)
│   ├── broadcaster.py
│   └── sse_helpers.py
│
├── persistence/             ✅ Single source (was: progress_persistence.py + persistence/)
│   └── progress.py
│
├── search/                  ✅ Consolidated (was: retrieval/ + search/)
│   ├── coarse_to_fine.py   # Moved from retrieval/
│   ├── search_service.py
│   └── ...
│
└── ...                      ✅ Other services organized
```

### Core Layer (Updated)
```
app/core/
└── validation/              ✅ Moved from services/validation/
    └── vector.py
```

---

## ⚠️ What Remains (Schemas & Workflows)

### Schemas Still Scattered (5 Locations)

```
app/
├── schemas/                      ⚠️ Location 1: API schemas only
│   ├── analyze.py
│   ├── artifact.py
│   ├── context.py
│   ├── library.py
│   └── search.py
│
├── workflows/
│   ├── agents/
│   │   └── schemas/              ⚠️ Location 2: Agent schemas (8 files)
│   │       ├── base.py
│   │       ├── code_quality_critic.py
│   │       ├── dependency_mapper.py
│   │       ├── implementation_planner.py
│   │       ├── integration_feasibility.py
│   │       ├── performance_analyst.py
│   │       ├── security_auditor.py
│   │       ├── tech_comparator.py
│   │       └── trend_validator.py
│   │
│   ├── tasks/
│   │   └── schemas/              ⚠️ Location 3: Task schemas (4 files)
│   │       ├── aggregated_insights.py
│   │       ├── core_synthesis.py
│   │       ├── docs_synthesis.py
│   │       └── learning_synthesis.py
│   │
│   └── tutor/
│       └── schemas/              ⚠️ Location 4: Tutor schemas (4 files)
│           ├── api.py
│           ├── assessment.py
│           ├── state.py
│           └── syllabus.py
│
└── evaluation/
    └── schemas/                  ⚠️ Location 5: Evaluation schemas (if exists)
```

**Impact**: 44 import statements reference these scattered locations.

---

### Workflows Still Deeply Nested

```
app/workflows/
├── agents/                       ⚠️ Agent implementations
│   ├── schemas/                  ❌ 3 levels deep
│   ├── validation/               ❌ 3 levels deep
│   └── [8 agent files]
│
├── nodes/                        ⚠️ Workflow nodes
│   └── agents/                   ❌ Confusing: agents/ vs nodes/agents/
│       └── [8 agent node files]
│
├── tasks/                        ⚠️ Task implementations
│   ├── schemas/                  ❌ 3 levels deep
│   ├── aggregation/              ❌ 3 levels deep
│   └── [15+ task files]
│
├── tutor/                        ⚠️ Tutor workflow
│   ├── schemas/                  ❌ 3 levels deep
│   ├── nodes/                    ❌ 3 levels deep
│   ├── tasks/                    ❌ 3 levels deep
│   └── [graph_builder, state, etc.]
│
└── utils/                        ✅ Shared utilities (good)
    └── [6 utility files]
```

**Issues**:
- Max nesting: 3-4 levels (should be max 3)
- No domain boundaries (analysis vs tutor mixed)
- Hard to find all "Analysis" code

---

## 📊 Current vs Target Comparison

### Finding "Implementation Planner Schema"

**CURRENT (After Cleanup):**
```
❌ workflows/agents/schemas/implementation_planner.py
   (3 levels deep, mixed with workflow code)
```

**TARGET:**
```
✅ domains/analysis/schemas/agents/implementation_planner.py
   (Clear domain boundary, max 3 levels)
```

---

### Finding "Tutor State Schema"

**CURRENT (After Cleanup):**
```
❌ workflows/tutor/schemas/state.py
   (3 levels deep, mixed with workflow code)
```

**TARGET:**
```
✅ domains/tutor/schemas/state.py
   (Clear domain boundary, 2 levels)
```

---

### Finding "All Analysis Code"

**CURRENT (After Cleanup):**
```
❌ Scattered across:
   - workflows/agents/
   - workflows/nodes/
   - workflows/tasks/
   - schemas/analyze.py
   - services/context/
   (Still hard to find everything!)
```

**TARGET:**
```
✅ Everything in domains/analysis/
   - domains/analysis/schemas/
   - domains/analysis/workflows/
   - domains/analysis/services/
   (One place for everything!)
```

---

## 🎯 Next Steps (Phase 7)

### Priority 1: Consolidate Schemas
- **Impact**: High (affects 44 imports)
- **Risk**: Medium (need compatibility imports)
- **Effort**: ~2-3 hours

### Priority 2: Consolidate Workflows
- **Impact**: Very High (affects 100+ imports)
- **Risk**: High (core functionality)
- **Effort**: ~4-6 hours

### Priority 3: Consolidate Services
- **Impact**: Medium (affects 30 imports)
- **Risk**: Low (services already organized)
- **Effort**: ~1-2 hours

---

## 📈 Progress Metrics

| Category | Status | Files | Imports to Update |
|----------|--------|-------|-------------------|
| **Services** | ✅ Done | 8 deleted | 8 updated |
| **Schemas** | ⚠️ Remaining | 16 files | 44 imports |
| **Workflows** | ⚠️ Remaining | 50+ files | 100+ imports |
| **Services (domain)** | ⚠️ Remaining | 10 files | 30 imports |

**Overall Progress**: ~15% complete (services layer done, schemas/workflows remain)

---

## 🔍 Quick Reference: Current Import Patterns

### Current Import Locations
```python
# API schemas
from app.schemas.analyze import AnalyzeRequest

# Agent schemas (3 levels deep)
from app.workflows.agents.schemas.implementation_planner import ImplementationPlan

# Task schemas (3 levels deep)
from app.workflows.tasks.schemas.core_synthesis import CoreSynthesisSchema

# Tutor schemas (3 levels deep)
from app.workflows.tutor.schemas.state import TutorState

# Services (✅ Already fixed)
from app.services.embeddings.service import EmbeddingService
from app.services.messaging.sse_helpers import emit_streaming_event
```

### Target Import Locations (After Phase 7-9)
```python
# API schemas (domain-based)
from app.domains.analysis.schemas.api import AnalyzeRequest

# Agent schemas (domain-based, 3 levels)
from app.domains.analysis.schemas.agents.implementation_planner import ImplementationPlan

# Task schemas (domain-based, 3 levels)
from app.domains.analysis.schemas.tasks.core_synthesis import CoreSynthesisSchema

# Tutor schemas (domain-based, 2 levels)
from app.domains.tutor.schemas.state import TutorState

# Services (✅ Already correct)
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.messaging.sse_helpers import emit_streaming_event
```

---

**Last Updated**: 2025-01-XX  
**Next Phase**: Phase 7 - Schema Consolidation  
**See**: `FOLDER_STRUCTURE_MIGRATION_PLAN.md` for detailed steps

