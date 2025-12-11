# Parallel Sprint Execution Plan

## Overview

This document outlines the strategy for running multiple sprints in parallel using Git worktrees and separate Claude Code instances. Based on dependency analysis of GitHub issues, we can safely parallelize certain sprints while respecting blocking dependencies.

## Current Setup

| Worktree | Sprint | Branch | Claude Instance |
|----------|--------|--------|-----------------|
| `SkillForge/` (main) | **8** | `feature/223-retrieval-smoke-tests` | ✅ **Active** |
| `SkillForge-sprint-9/` | 9 | `feature/sprint-9-mcp` | Ready to launch |
| `SkillForge-sprint-12/` | 12 | `feature/sprint-12-eval-datasets` | Ready to launch |

## Sprint Status Matrix

| Sprint | Milestone | Status | Can Parallelize? | Blocking Dependency |
|--------|-----------|--------|------------------|---------------------|
| **8** | Embeddings & Vector Search | **Active (main worktree)** | ✅ Yes | None |
| **9** | MCP Server Foundation | Ready | ✅ Yes | None |
| **11** | Context Engineering & RAG | Blocked | ❌ No | Sprint 8 (#219 embeddings) |
| **12** | Evaluation Datasets v2.0 | Ready | ✅ Yes | None |

## Dependency Graph

```
Sprint 8 (Embeddings)          Sprint 9 (MCP)           Sprint 12 (Eval Datasets)
━━━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━           ━━━━━━━━━━━━━━━━━━━━━━━━
#219 Embedding A/B             #230 MCP Client Pool     #251-260 Dataset v2.0
#220 Vector Search             #231 Tool Registry
#221 Batch Processing          #232 Auth/Permissions
        │                              │                         │
        │                              │                         │
        ▼                              ▼                         ▼
   [BLOCKS]                      [Independent]            [Independent]
        │
        ▼
Sprint 11 (RAG Memory)
━━━━━━━━━━━━━━━━━━━━━
#245 RAG Memory System
     └── uses similarity_search()
         from embeddings service
```

## Why Sprint 11 Must Wait

Issue #245 (Context Engineering RAG Memory) depends on the embeddings infrastructure:

```python
# From Sprint 11 implementation (requires Sprint 8 complete):
results = await embeddings_service.similarity_search(
    query_embedding,
    collection="learning_context",
    top_k=10
)
```

This `similarity_search()` method is implemented in Sprint 8's embedding service (#219, #220).

## File Isolation Verification

Each sprint operates on isolated file paths with no conflicts:

| Sprint | Primary Paths | No Conflicts With |
|--------|---------------|-------------------|
| 8 | `backend/app/services/embeddings/` | 9, 12 |
| 9 | `backend/app/mcp/`, `backend/app/services/mcp_*` | 8, 12 |
| 12 | `backend/app/evaluation/datasets/`, `backend/app/evaluation/schemas/` | 8, 9 |

## Worktree Setup Commands

### Current Setup (Sprint 8 Already Active)

Sprint 8 is already running on the main worktree (`feature/223-retrieval-smoke-tests`).

```bash
# From main repository (Sprint 8 already active here)
cd /Users/yonatangross/coding/SkillForge

# Create worktrees for Sprint 9 and 12 only
git worktree add ../SkillForge-sprint-9 -b feature/sprint-9-mcp
git worktree add ../SkillForge-sprint-12 -b feature/sprint-12-eval-datasets

# Verify worktrees
git worktree list
```

### Launch Claude Instances

```bash
# Terminal 1 - Sprint 8 (ALREADY RUNNING)
# Main worktree: /Users/yonatangross/coding/SkillForge
# Branch: feature/223-retrieval-smoke-tests

# Terminal 2 - Sprint 9
cd ../SkillForge-sprint-9 && claude

# Terminal 3 - Sprint 12
cd ../SkillForge-sprint-12 && claude
```

## Phase Transitions

### Phase 1: Parallel Execution (Now)
- ✅ Sprint 8: Embeddings & Vector Search
- ✅ Sprint 9: MCP Server Foundation
- ✅ Sprint 12: Evaluation Datasets v2.0

### Phase 2: Sprint 11 Unlocked (After Sprint 8 Merges)
```bash
# When Sprint 8 is merged to main:
git worktree add ../SkillForge-sprint-11 feature/sprint-11-rag-memory

# Sprint 11 can now proceed with embeddings available
```

## Merge Strategy

```
main ─────●─────────●─────────●─────────●─────────→
          │         │         │         │
          │    Sprint 9   Sprint 12   Sprint 8
          │    (merge)    (merge)     (merge)
          │                               │
          │                               ▼
          │                          Sprint 11
          │                          (can start)
          │                               │
          └───────────────────────────────┴─→ main
```

### Recommended Merge Order
1. **Sprint 9** (MCP) - No dependencies, can merge first
2. **Sprint 12** (Eval) - No dependencies, can merge anytime
3. **Sprint 8** (Embeddings) - Unlocks Sprint 11
4. **Sprint 11** (RAG) - After Sprint 8 merged

## Conflict Prevention Rules

1. **Never modify shared files** across worktrees simultaneously
2. **Coordinate on shared types** - if one sprint adds types to `backend/app/core/types.py`, others wait
3. **Database migrations** - only one sprint can add migrations at a time, coordinate numbers
4. **Dependencies** - if adding to `pyproject.toml`, sync across worktrees before committing

## Shared Files Requiring Coordination

| File | Sprints Using | Coordination Strategy |
|------|---------------|----------------------|
| `pyproject.toml` | 8, 9, 11 | Sync before final commit |
| `backend/app/core/config.py` | 8, 9, 11 | Add settings in isolated sections |
| `alembic/versions/` | 8, 9 | Coordinate revision numbers |

## Communication Protocol

When running parallel Claude instances:

1. **Shared Context File**: All instances read/write to `.claude/context/shared-context.json`
2. **Lock Announcements**: Before modifying shared files, document in shared context
3. **Completion Signals**: Mark sprint milestones in shared context for other instances

## Quick Reference

```bash
# List all worktrees
git worktree list

# Remove a worktree (after merging)
git worktree remove ../SkillForge-sprint-9

# Prune stale worktree references
git worktree prune
```

---

*Document created: December 2024*
*Based on GitHub issues analysis for Sprints 8, 9, 11, 12*
