# Folder Structure Migration Plan (Updated)

**Status**: Phase 1-6 Complete ✅ | Phase 7+ In Progress

## 📋 Executive Summary

**What's Done** (Phases 1-6):
- ✅ Removed 8 duplicate service files
- ✅ Consolidated services (embeddings, messaging, persistence, search)
- ✅ Moved validation/ to core/validation/
- ✅ Fixed 8 import paths
- ✅ Verified: 66/69 tests passing, all imports working

**What Remains** (Phases 7-10):
- ⚠️ Consolidate schemas from 5 locations → domain-based (44 imports)
- ⚠️ Consolidate workflows → domain-based (100+ imports)
- ⚠️ Move domain services → domains/ (30 imports)
- ⚠️ Final cleanup and documentation

**Progress**: ~15% complete (services layer done, schemas/workflows remain)

**Next Step**: Phase 7 - Schema Consolidation (see Quick Start section below)

---

## ✅ Completed Phases (2025-01-XX)

### Phase 1: Deleted Duplicate Old Files ✅
- Removed 8 old service files that were moved to subdirectories:
  - `services/embeddings.py` → `services/embeddings/service.py`
  - `services/embeddings_deterministic.py` → `services/embeddings/deterministic.py`
  - `services/embeddings_utils.py` → `services/embeddings/utils.py`
  - `services/sse_helpers.py` → `services/messaging/sse_helpers.py`
  - `services/progress_persistence.py` → `services/persistence/progress.py`
  - And 3 others

### Phase 2: Removed Old Directories ✅
- Deleted `services/validation/` → moved to `core/validation/`
- Deleted `services/retrieval/` → moved to `search/` (coarse_to_fine.py)

### Phase 3: Fixed Import Paths ✅
- Updated 8 files to use new import paths:
  - `services/__init__.py`
  - `workflows/tasks/generate_embedding.py`
  - `services/search/search_service.py`
  - `services/memory/agent_memory_service.py`
  - `api/v1/search.py`
  - `api/v1/library.py`
  - `evaluation/pipeline/runner.py`
  - `services/memory/proactive_recall.py`

### Phase 4-6: Verification ✅
- All imports working (verified with Python import test)
- No old import paths remaining (grep confirmed)
- 66 tests passing in core service tests
- All code formatted
- No critical lint errors

**Note**: 3 failing tests are functional issues (SSE database connection, embedding patch), not import problems.

---

## 🎯 Remaining Work

### Current State After Cleanup

```
app/
├── api/v1/                    ✅ Clean
├── schemas/                   ⚠️ Only API schemas (5 locations total)
├── services/                  ✅ Clean (no duplicates)
├── workflows/                 ⚠️ Still has deep nesting + scattered schemas
│   ├── agents/
│   │   └── schemas/          ❌ 3 levels deep
│   ├── tasks/
│   │   └── schemas/          ❌ 3 levels deep
│   ├── tutor/
│   │   └── schemas/          ❌ 3 levels deep
│   └── nodes/
│       └── agents/           ❌ 3 levels deep
└── evaluation/
    └── schemas/               ❌ Separate location
```

### Remaining Issues

1. **Schemas Scattered** (5 locations):
   - `app/schemas/` - API schemas only
   - `app/workflows/agents/schemas/` - Agent schemas (8 files)
   - `app/workflows/tasks/schemas/` - Task schemas (4 files)
   - `app/workflows/tutor/schemas/` - Tutor schemas (4 files)
   - `app/evaluation/schemas/` - Evaluation schemas (if exists)

2. **Deep Nesting** (3-4 levels):
   - `workflows/agents/schemas/` - 3 levels
   - `workflows/tasks/schemas/` - 3 levels
   - `workflows/tutor/schemas/` - 3 levels
   - `workflows/nodes/agents/` - 3 levels

3. **No Domain Boundaries**:
   - Still organized by technical layer (agents, nodes, tasks)
   - Hard to find all "Analysis" or "Tutor" code

---

## 📋 Updated Migration Plan

### Phase 7: Consolidate Schemas (Incremental, Non-Breaking)

**Goal**: Move all schemas to domain-based locations without breaking imports.

#### Step 7.1: Create Domain Structure (Non-Breaking)
```bash
# Create new structure alongside old
mkdir -p app/domains/analysis/schemas/{api,agents,tasks,state}
mkdir -p app/domains/tutor/schemas/{api,state,assessment,syllabus}
mkdir -p app/shared/schemas
```

#### Step 7.2: Move Analysis Schemas
```bash
# Move API schemas
mv app/schemas/analyze.py app/domains/analysis/schemas/api.py
mv app/schemas/artifact.py app/domains/analysis/schemas/api.py  # Merge or keep separate?

# Move agent schemas
mv app/workflows/agents/schemas/* app/domains/analysis/schemas/agents/

# Move task schemas
mv app/workflows/tasks/schemas/* app/domains/analysis/schemas/tasks/

# Move workflow state
# (Keep workflows/state.py for now, or move to domains/analysis/schemas/state.py?)
```

#### Step 7.3: Move Tutor Schemas
```bash
# Move tutor schemas
mv app/workflows/tutor/schemas/api.py app/domains/tutor/schemas/api.py
mv app/workflows/tutor/schemas/state.py app/domains/tutor/schemas/state.py
mv app/workflows/tutor/schemas/assessment.py app/domains/tutor/schemas/assessment.py
mv app/workflows/tutor/schemas/syllabus.py app/domains/tutor/schemas/syllabus.py
```

#### Step 7.4: Create Compatibility Imports
```python
# app/workflows/agents/schemas/__init__.py (temporary compatibility)
from app.domains.analysis.schemas.agents import *
# Keep for backward compatibility during migration
```

#### Step 7.5: Update Imports Gradually
- Start with low-risk files (tests, utilities)
- Update workflow files in batches
- Run tests after each batch

**Estimated Impact**: ~44 import statements to update (from grep results)

---

### Phase 8: Consolidate Workflows (Domain-Driven)

**Goal**: Move workflows to domain structure.

#### Step 8.1: Move Analysis Workflows
```bash
# Create structure
mkdir -p app/domains/analysis/workflows/{agents,nodes,tasks}

# Move agents
mv app/workflows/agents/* app/domains/analysis/workflows/agents/
# (except schemas/, already moved)

# Move nodes
mv app/workflows/nodes/* app/domains/analysis/workflows/nodes/

# Move tasks
mv app/workflows/tasks/* app/domains/analysis/workflows/tasks/

# Move workflow files
mv app/workflows/analysis.py app/domains/analysis/workflows/
mv app/workflows/graph_builder.py app/domains/analysis/workflows/
mv app/workflows/state.py app/domains/analysis/workflows/  # Or keep shared?
```

#### Step 8.2: Move Tutor Workflows
```bash
# Move tutor workflows
mv app/workflows/tutor/* app/domains/tutor/workflows/
# (schemas already moved in Phase 7)
```

#### Step 8.3: Move Shared Workflow Utils
```bash
# Move shared utilities
mv app/workflows/utils/* app/shared/workflows/utils/
mv app/workflows/prompts/ app/shared/workflows/prompts/
```

#### Step 8.4: Update All Imports
- Update ~100+ import statements
- Run full test suite after each domain

---

### Phase 9: Consolidate Services (Domain-Specific)

**Goal**: Move domain-specific services to domains.

#### Step 9.1: Identify Domain Services
```bash
# Analysis domain services
services/context/          → domains/analysis/services/context/
services/tutor/            → domains/tutor/services/  # Already exists!

# Shared services (keep in shared/)
services/embeddings/       → shared/services/embeddings/
services/extraction/       → shared/services/extraction/
services/chunking/         → shared/services/chunking/
services/messaging/        → shared/services/messaging/
services/search/           → shared/services/search/
services/persistence/     → shared/services/persistence/
```

#### Step 9.2: Move Services
```bash
# Move analysis services
mv app/services/context app/domains/analysis/services/

# Move tutor services (already in services/tutor/)
mv app/services/tutor app/domains/tutor/services/

# Move shared services
mkdir -p app/shared/services
mv app/services/{embeddings,extraction,chunking,messaging,search,persistence} app/shared/services/
```

---

### Phase 10: Final Cleanup

#### Step 10.1: Remove Old Directories
```bash
# After all imports updated
rm -rf app/workflows/agents/schemas/
rm -rf app/workflows/tasks/schemas/
rm -rf app/workflows/tutor/schemas/
rm -rf app/workflows/agents/  # (if everything moved)
rm -rf app/workflows/tasks/   # (if everything moved)
rm -rf app/workflows/tutor/   # (if everything moved)
rm -rf app/schemas/           # (if everything moved)
```

#### Step 10.2: Update Documentation
- Update `docs/ARCHITECTURE.md`
- Update `docs/YONATAN_BACKEND_TASKS.md`
- Update import examples in README

#### Step 10.3: Verify Everything
```bash
# Run full test suite
pytest tests/ -v

# Check for old imports
grep -r "from app\.workflows\.agents\.schemas" app/
grep -r "from app\.workflows\.tasks\.schemas" app/
grep -r "from app\.workflows\.tutor\.schemas" app/
grep -r "from app\.schemas\." app/  # Should only find API imports

# Check linting
ruff check app/
mypy app/
```

---

## 🎯 Final Target Structure

```
app/
├── api/v1/                    🌐 API Layer
│
├── domains/                   🏗️ Domain Layer
│   ├── analysis/
│   │   ├── schemas/          ✅ All analysis schemas
│   │   ├── workflows/        ✅ All analysis workflows
│   │   └── services/         ✅ Analysis-specific services
│   │
│   ├── tutor/
│   │   ├── schemas/          ✅ All tutor schemas
│   │   ├── workflows/        ✅ All tutor workflows
│   │   └── services/         ✅ Tutor-specific services
│   │
│   └── evaluation/
│       ├── schemas/          ✅ Evaluation schemas
│       └── workflows/        ✅ Evaluation workflows
│
├── shared/                    🔧 Shared Infrastructure
│   ├── schemas/              ✅ Shared schemas
│   ├── services/             ✅ Shared services
│   └── workflows/            ✅ Shared workflow utils
│
├── db/                        💾 Data Access
├── models/                    🗄️ DB Models
└── core/                      ⚙️ Core Config
```

---

## 📊 Progress Tracking

| Phase | Status | Files Moved | Imports Updated | Tests Passing |
|-------|--------|-------------|------------------|---------------|
| 1-6   | ✅ Done | 8 deleted | 8 updated | 66/69 |
| 7     | 🔄 Next | ~16 schemas | ~44 imports | TBD |
| 8     | ⏳ Pending | ~50 workflows | ~100 imports | TBD |
| 9     | ⏳ Pending | ~10 services | ~30 imports | TBD |
| 10    | ⏳ Pending | Cleanup | Final verify | TBD |

---

## ⚠️ Migration Principles

1. **Non-Breaking**: Keep compatibility imports during migration
2. **Incremental**: Move one domain at a time
3. **Tested**: Run tests after each phase
4. **Reversible**: Use git branches, can revert if needed
5. **Documented**: Update docs as we go

---

## 🚀 Quick Start: Phase 7

To start Phase 7 (Schema Consolidation):

```bash
# 1. Create feature branch
git checkout -b refactor/phase7-consolidate-schemas

# 2. Create domain structure
mkdir -p app/domains/analysis/schemas/{api,agents,tasks,state}
mkdir -p app/domains/tutor/schemas/{api,state,assessment,syllabus}
mkdir -p app/shared/schemas

# 3. Move schemas (start with one domain)
# See Step 7.2-7.3 above

# 4. Create compatibility imports
# See Step 7.4 above

# 5. Update imports gradually
# See Step 7.5 above

# 6. Test and commit
pytest tests/ -v
git commit -m "refactor: consolidate analysis schemas to domains/"
```

---

**Last Updated**: 2025-01-XX  
**Next Phase**: Phase 7 - Schema Consolidation

