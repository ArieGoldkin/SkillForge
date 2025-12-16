# Folder Structure Refactoring Proposal

## Current State (Issues Identified)

```
backend/app/
├── api/                          # ✅ Good: API layer separation
│   └── v1/
│       ├── analyze.py
│       ├── tutor/
│       └── ...
│
├── schemas/                      # ⚠️ ISSUE: Only API schemas here
│   ├── analyze.py
│   ├── artifact.py
│   └── ...
│
├── models/                       # ✅ Good: DB models centralized
│   ├── analysis.py
│   ├── artifact.py
│   └── ...
│
├── services/                     # ✅ CLEANED: Duplicates removed
│   ├── embeddings/              # ✅ Single source of truth
│   │   ├── service.py
│   │   ├── deterministic.py
│   │   └── utils.py
│   ├── messaging/               # ✅ Single source of truth
│   │   └── sse_helpers.py
│   ├── persistence/             # ✅ Single source of truth
│   │   └── progress.py
│   ├── extraction/              # ✅ Good: Organized
│   ├── chunking/                 # ✅ Good: Organized
│   ├── search/                  # ✅ Moved from retrieval/
│   └── ...
│
└── workflows/                    # ⚠️ MAJOR ISSUE: Deep nesting, mixed concerns
    ├── agents/                  # Agent implementations
    │   ├── schemas/             # ❌ Schemas nested 2 levels deep
    │   │   ├── base.py
    │   │   ├── implementation_planner.py
    │   │   └── ...
    │   ├── validation/          # ❌ Validation nested 2 levels deep
    │   └── ...
    │
    ├── nodes/                   # Workflow nodes
    │   └── agents/              # ❌ Confusing: agents/ vs nodes/agents/
    │       ├── implementation_planner_node.py
    │       └── ...
    │
    ├── tasks/                   # Task implementations
    │   ├── schemas/             # ❌ Schemas nested 2 levels deep
    │   │   ├── core_synthesis.py
    │   │   └── ...
    │   ├── aggregation/         # ❌ Deep nesting
    │   └── ...
    │
    ├── tutor/                   # Tutor workflow
    │   ├── schemas/             # ❌ Schemas nested 2 levels deep
    │   ├── nodes/               # ❌ Deep nesting
    │   └── tasks/               # ❌ Deep nesting
    │
    ├── evaluation/               # Evaluation workflow
    │   └── ...
    │
    └── state.py                 # ✅ Good: Shared state
```

### Problems Identified

1. **Schemas Scattered** (5 locations):
   - `app/schemas/` - API schemas only
   - `app/workflows/agents/schemas/` - Agent schemas
   - `app/workflows/tasks/schemas/` - Task schemas
   - `app/workflows/tutor/schemas/` - Tutor schemas
   - `app/evaluation/schemas/` - Evaluation schemas

2. **Deep Nesting** (3-4 levels):
   - `workflows/agents/schemas/` - 3 levels
   - `workflows/tasks/aggregation/` - 3 levels
   - `workflows/tutor/nodes/` - 3 levels

3. **Duplicate Files**: ✅ FIXED (Phase 1-2 Complete)
   - ~~`services/embeddings.py` vs `services/embeddings/service.py`~~ → Removed
   - ~~`services/sse_helpers.py` vs `services/messaging/sse_helpers.py`~~ → Removed
   - ~~`services/progress_persistence.py` vs `services/persistence/progress.py`~~ → Removed
   - ~~`services/validation/`~~ → Moved to `core/validation/`
   - ~~`services/retrieval/`~~ → Moved to `services/search/`

4. **Confusing Organization**:
   - `workflows/agents/` vs `workflows/nodes/agents/` - unclear relationship
   - Mixed technical layers (agents, nodes, tasks) instead of domain boundaries

5. **No Domain Boundaries**:
   - Everything organized by technical layer, not business domain
   - Hard to find all code related to "Analysis" or "Tutor"

---

## Proposed Structure (Domain-Driven + Clean Architecture)

```
backend/app/
│
├── api/                          # 🌐 API Layer (Thin, delegates to domains)
│   ├── v1/
│   │   ├── analyze.py           # → domains.analysis.api
│   │   ├── tutor/               # → domains.tutor.api
│   │   ├── library.py           # → domains.library.api
│   │   └── search.py            # → domains.search.api
│   └── dependencies.py          # Shared API dependencies
│
├── domains/                      # 🏗️ Domain Layer (Business Logic)
│   │
│   ├── analysis/                # 📊 Analysis Domain
│   │   ├── __init__.py
│   │   │
│   │   ├── schemas/             # ✅ All analysis schemas in one place
│   │   │   ├── __init__.py
│   │   │   ├── api.py           # API request/response schemas
│   │   │   ├── state.py         # Workflow state schemas
│   │   │   ├── agents/          # Agent output schemas
│   │   │   │   ├── base.py
│   │   │   │   ├── implementation_planner.py
│   │   │   │   ├── tech_comparator.py
│   │   │   │   └── ...
│   │   │   └── tasks/           # Task output schemas
│   │   │       ├── synthesis.py
│   │   │       └── aggregation.py
│   │   │
│   │   ├── workflows/           # ✅ All analysis workflows
│   │   │   ├── __init__.py
│   │   │   ├── graph_builder.py
│   │   │   ├── state.py
│   │   │   ├── agents/          # Agent implementations
│   │   │   │   ├── implementation_planner.py
│   │   │   │   ├── tech_comparator.py
│   │   │   │   └── ...
│   │   │   ├── nodes/           # Workflow nodes
│   │   │   │   ├── extract_content.py
│   │   │   │   ├── chunk_content.py
│   │   │   │   ├── agent_router.py
│   │   │   │   └── agents/      # Agent nodes
│   │   │   │       ├── implementation_planner_node.py
│   │   │   │       └── ...
│   │   │   └── tasks/           # Task implementations
│   │   │       ├── aggregation/
│   │   │       ├── synthesis.py
│   │   │       └── ...
│   │   │
│   │   ├── services/            # ✅ Domain-specific services
│   │   │   ├── __init__.py
│   │   │   ├── artifact_service.py
│   │   │   └── context_service.py
│   │   │
│   │   └── models.py            # Domain models (if any beyond DB)
│   │
│   ├── tutor/                   # 🎓 Tutor Domain
│   │   ├── __init__.py
│   │   ├── schemas/
│   │   │   ├── api.py
│   │   │   ├── state.py
│   │   │   ├── syllabus.py
│   │   │   └── assessment.py
│   │   ├── workflows/
│   │   │   ├── graph_builder.py
│   │   │   ├── state.py
│   │   │   ├── nodes/
│   │   │   │   ├── ask_socratic.py
│   │   │   │   ├── deliver_lesson.py
│   │   │   │   └── ...
│   │   │   └── tasks/
│   │   │       ├── syllabus_generation.py
│   │   │       └── lesson_delivery.py
│   │   └── services/
│   │       ├── state_service.py
│   │       └── analysis_service.py
│   │
│   ├── evaluation/              # 📈 Evaluation Domain
│   │   ├── __init__.py
│   │   ├── schemas/
│   │   │   └── dataset_v2_schema.json
│   │   ├── workflows/
│   │   │   ├── evaluator.py
│   │   │   └── optimizer.py
│   │   ├── services/
│   │   │   ├── correctness.py
│   │   │   ├── quality.py
│   │   │   └── ...
│   │   └── datasets/            # Evaluation datasets
│   │
│   └── library/                 # 📚 Library Domain (if needed)
│       ├── schemas/
│       └── services/
│
├── shared/                      # 🔧 Shared Infrastructure
│   ├── schemas/                 # ✅ Shared schemas
│   │   ├── base.py              # Base Pydantic models
│   │   └── common.py            # Common types
│   │
│   ├── services/                # ✅ Shared services (cross-domain)
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   ├── service.py       # ✅ Single source of truth
│   │   │   ├── deterministic.py
│   │   │   └── utils.py
│   │   ├── extraction/
│   │   │   ├── jina_reader.py
│   │   │   └── content_cleaner.py
│   │   ├── chunking/
│   │   │   ├── chunker.py
│   │   │   └── parsers.py
│   │   ├── messaging/
│   │   │   ├── broadcaster.py
│   │   │   └── sse_helpers.py   # ✅ Single source of truth
│   │   ├── persistence/
│   │   │   └── progress.py      # ✅ Single source of truth
│   │   ├── search/
│   │   │   ├── search_service.py
│   │   │   └── reranker.py
│   │   └── validation/
│   │       └── vector_validator.py
│   │
│   └── workflows/               # ✅ Shared workflow utilities
│       ├── utils/
│       │   ├── content_signals.py
│       │   └── retrieval_routing.py
│       └── prompts/             # Shared prompts
│
├── db/                          # 💾 Data Access Layer
│   ├── base.py
│   ├── session.py
│   └── repositories/            # ✅ Repository pattern
│       ├── analysis_repository.py
│       ├── artifact_repository.py
│       └── ...
│
├── models/                      # 🗄️ Database Models (SQLAlchemy)
│   ├── analysis.py
│   ├── artifact.py
│   └── ...
│
└── core/                        # ⚙️ Core Configuration
    ├── config.py
    ├── logging.py
    ├── tracing.py
    └── ...
```

---

## Key Improvements

### 1. **Domain-Driven Organization** ✅
- All code for "Analysis" is in `domains/analysis/`
- All code for "Tutor" is in `domains/tutor/`
- Easy to find and understand domain boundaries

### 2. **Centralized Schemas** ✅
- Domain schemas: `domains/{domain}/schemas/`
- Shared schemas: `shared/schemas/`
- No more hunting across 5 locations

### 3. **Eliminated Duplicates** ✅
- Single source of truth for embeddings, SSE, persistence
- Clear ownership: shared services in `shared/services/`

### 4. **Reduced Nesting** ✅
- Max 3 levels deep (was 4)
- Clear hierarchy: `domains/{domain}/{layer}/{component}`

### 5. **Clear Layer Separation** ✅
```
API Layer      → domains/{domain}/schemas/api.py
Domain Layer   → domains/{domain}/workflows/
Infrastructure → shared/services/
Data Layer     → db/repositories/
```

### 6. **Better Discoverability** ✅
- Want analysis code? → `domains/analysis/`
- Want tutor code? → `domains/tutor/`
- Want shared utilities? → `shared/`

---

## Migration Strategy

### ✅ Phase 1-6: COMPLETE (2025-01-XX)
- **Phase 1**: Deleted 8 duplicate service files
- **Phase 2**: Removed old directories (validation/, retrieval/)
- **Phase 3**: Fixed 8 import paths
- **Phase 4-6**: Verification (66/69 tests passing, imports working)

**See**: `docs/architecture/FOLDER_STRUCTURE_MIGRATION_PLAN.md` for detailed progress.

### 🔄 Phase 7: Consolidate Schemas (Next)
1. Create `domains/` structure for schemas
2. Move schemas from 5 locations to domain-based structure
3. Update ~44 import statements gradually
4. Keep compatibility imports during migration

### ⏳ Phase 8: Consolidate Workflows
1. Move workflows to domain structure
2. Update ~100+ import statements
3. Move shared utilities to `shared/workflows/`

### ⏳ Phase 9: Consolidate Services
1. Move domain-specific services to domains
2. Move shared services to `shared/services/`
3. Update ~30 import statements

### ⏳ Phase 10: Final Cleanup
1. Remove old empty directories
2. Update documentation
3. Final verification

---

## Benefits

1. **Maintainability**: Clear domain boundaries make code easier to understand
2. **Scalability**: Easy to add new domains (e.g., `domains/workspace/`)
3. **Testability**: Domain code is isolated and testable
4. **Onboarding**: New developers can find code faster
5. **Refactoring**: Changes to one domain don't affect others

---

## Comparison: Finding Code

### Current (Scattered)
```
Where is the implementation planner schema?
→ workflows/agents/schemas/implementation_planner.py

Where is the tutor state schema?
→ workflows/tutor/schemas/state.py

Where is the SSE helper?
→ services/sse_helpers.py OR services/messaging/sse_helpers.py? 🤔
```

### Proposed (Organized)
```
Where is the implementation planner schema?
→ domains/analysis/schemas/agents/implementation_planner.py

Where is the tutor state schema?
→ domains/tutor/schemas/state.py

Where is the SSE helper?
→ shared/services/messaging/sse_helpers.py ✅
```

---

**Last Updated**: 2025-01-XX  
**Status**: Proposal - Awaiting Review

