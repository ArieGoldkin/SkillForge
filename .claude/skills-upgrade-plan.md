# Skills Gold Standard Upgrade Plan

**Goal:** Bring all 27 skills to 6/6 components (Gold Standard)
**Created:** December 21, 2025
**Estimated Total Effort:** 12-15 hours across 4 phases

---

## Current State Summary

| Status | Count | % | Skills |
|--------|-------|---|--------|
| 🏆 Gold (6/6) | 3 | 11% | ai-native-development, browser-content-capture, react-server-components-framework |
| ✅ Near (5/6) | 7 | 26% | langgraph-workflows, llm-caching-patterns, pgvector-search, architecture-decision-record, design-system-starter, testing-strategy-builder, github-cli |
| ⚡ Good (4/6) | 10 | 37% | api-design-framework, brainstorming, code-review-playbook, devops-deployment, evidence-verification, golden-dataset-management, langfuse-observability, observability-monitoring, performance-optimization, streaming-api-patterns |
| ⚠️ Work (3/6) | 5 | 19% | ascii-visualizer, database-schema-designer, quality-gates, security-checklist, webapp-testing |
| ❌ Skel (2/6) | 2 | 7% | edge-computing-patterns, type-safety-validation |

---

## Phase 1: Quick Wins (5/6 → 6/6)

**Effort:** LOW | **Skills:** 7 | **Time:** 2-3 hours

### Batch 1.1: Add Checklists (3 skills)

**Subagent:** `ai-ml-engineer` (parallel x1)

| Skill | Missing | File to Create |
|-------|---------|----------------|
| langgraph-workflows | K | `checklists/workflow-implementation-checklist.md` |
| llm-caching-patterns | K | `checklists/caching-implementation-checklist.md` |
| pgvector-search | K | `checklists/search-implementation-checklist.md` |

**Task Prompt:**
```
Create implementation checklists for 3 skills. Each checklist should:
- Follow existing checklist format in the codebase
- Include pre-implementation, implementation, and verification steps
- Be specific to the skill's domain
- Reference templates and references from the same skill
```

### Batch 1.2: Add References (1 skill)

**Subagent:** `backend-system-architect` (parallel x1)

| Skill | Missing | File to Create |
|-------|---------|----------------|
| architecture-decision-record | R | `references/adr-best-practices.md` |

### Batch 1.3: Add Examples (3 skills)

**Subagent:** `ai-ml-engineer` (parallel x1)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| design-system-starter | E | `examples/skillforge-design-system.md` |
| testing-strategy-builder | E | `examples/skillforge-test-strategy.md` |
| github-cli | E,K | `examples/skillforge-workflow.md`, `checklists/gh-cli-checklist.md` |

---

## Phase 2: Standard Upgrades (4/6 → 6/6)

**Effort:** MEDIUM | **Skills:** 10 | **Time:** 4-5 hours

### Batch 2.1: Backend Skills (4 skills)

**Subagent:** `backend-system-architect` (parallel x2)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| api-design-framework | R,E | `references/rest-patterns.md`, `examples/skillforge-api.md` |
| streaming-api-patterns | R,E | `references/sse-patterns.md`, `examples/skillforge-sse.md` |
| evidence-verification | R,K | `references/evidence-patterns.md`, `checklists/verification-checklist.md` |
| golden-dataset-management | E,K | `examples/dataset-workflow.md`, `checklists/backup-checklist.md` |

### Batch 2.2: Observability Skills (3 skills)

**Subagent:** `ai-ml-engineer` (parallel x2)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| langfuse-observability | E,K | `examples/skillforge-traces.md`, `checklists/observability-checklist.md` |
| observability-monitoring | E,K | `examples/metrics-dashboard.md`, `checklists/monitoring-checklist.md` |
| performance-optimization | E,K | `examples/query-optimization.md`, `checklists/performance-checklist.md` |

### Batch 2.3: Process Skills (3 skills)

**Subagent:** `code-quality-reviewer` (parallel x1)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| brainstorming | E,K | `examples/feature-brainstorm.md`, `checklists/brainstorm-checklist.md` |
| code-review-playbook | R,E | `references/review-patterns.md`, `examples/skillforge-review.md` |
| devops-deployment | E,K | `examples/skillforge-deploy.md`, `checklists/deploy-checklist.md` |

---

## Phase 3: Major Upgrades (3/6 → 6/6)

**Effort:** HIGH | **Skills:** 5 | **Time:** 3-4 hours

### Batch 3.1: Quality & Security (2 skills)

**Subagent:** `code-quality-reviewer` (parallel x1)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| quality-gates | R,E,K | `references/gate-patterns.md`, `examples/skillforge-gates.md`, `checklists/gate-checklist.md` |
| security-checklist | R,T,E | `references/owasp-mitigations.md`, `templates/security-audit.md`, `examples/skillforge-security.md` |

### Batch 3.2: Testing & Visualization (2 skills)

**Subagent:** `frontend-ui-developer` (parallel x1)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| webapp-testing | T,E,K | `templates/playwright-test.ts`, `examples/skillforge-e2e.md`, `checklists/e2e-checklist.md` |
| ascii-visualizer | T,E,K | `templates/diagram-template.md`, `examples/architecture-example.md`, `checklists/diagram-checklist.md` |

### Batch 3.3: Database Design (1 skill)

**Subagent:** `backend-system-architect` (parallel x1)

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| database-schema-designer | R,T,E | `references/normalization-patterns.md`, `templates/schema-template.sql`, `examples/skillforge-schema.md` |

---

## Phase 4: Full Build (2/6 → 6/6)

**Effort:** VERY HIGH | **Skills:** 2 | **Time:** 2-3 hours

### Batch 4.1: Edge Computing

**Subagent:** `frontend-ui-developer`

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| edge-computing-patterns | R,T,E,K | - `references/cloudflare-workers.md` |
| | | - `references/vercel-edge.md` |
| | | - `references/runtime-differences.md` |
| | | - `templates/edge-function.ts` |
| | | - `templates/middleware.ts` |
| | | - `examples/edge-caching.md` |
| | | - `checklists/edge-deploy-checklist.md` |

### Batch 4.2: Type Safety

**Subagent:** `frontend-ui-developer`

| Skill | Missing | Files to Create |
|-------|---------|-----------------|
| type-safety-validation | R,T,E,K | - `references/zod-patterns.md` |
| | | - `references/trpc-setup.md` |
| | | - `references/prisma-types.md` |
| | | - `templates/zod-schema.ts` |
| | | - `templates/trpc-router.ts` |
| | | - `examples/skillforge-types.md` |
| | | - `checklists/type-safety-checklist.md` |

---

## Execution Strategy

### Parallel Execution Plan

```
Phase 1 (2-3 hrs):  [Agent 1]──────────────────►
                    [Agent 2]──────────────────►
                    [Agent 3]──────────────────►

Phase 2 (4-5 hrs):  [Agent 1]─────────────────────────────────────►
                    [Agent 2]─────────────────────────────────────►
                    [Agent 3]─────────────────────────────────────►
                    [Agent 4]─────────────────────────────────────►

Phase 3 (3-4 hrs):  [Agent 1]──────────────────────────────►
                    [Agent 2]──────────────────────────────►
                    [Agent 3]──────────────────────────────►

Phase 4 (2-3 hrs):  [Agent 1]──────────────────────────────►
                    [Agent 2]──────────────────────────────►
```

### Quality Gates

Each batch must pass:
1. ✅ All files created with content (no empty files)
2. ✅ Files follow existing skill conventions
3. ✅ SkillForge-specific examples where applicable
4. ✅ Cross-references to related skills
5. ✅ capabilities.json updated if new capabilities added

### Verification Command

After each phase:
```bash
cd .claude/skills && find . -maxdepth 3 -type f | wc -l
# Expected: Phase 1: +10, Phase 2: +20, Phase 3: +15, Phase 4: +14
```

---

## File Count Targets

| Phase | Skills | Files Added | Cumulative |
|-------|--------|-------------|------------|
| Start | 27 | - | 184 |
| Phase 1 | 7 | 10 | 194 |
| Phase 2 | 10 | 20 | 214 |
| Phase 3 | 5 | 15 | 229 |
| Phase 4 | 2 | 14 | 243 |

**Final Target:** 243 files, 27 skills at 6/6 (100% Gold Standard)

---

## Invocation Commands

### Phase 1 (Run in parallel)
```
Task: ai-ml-engineer - "Create checklists for langgraph-workflows, llm-caching-patterns, pgvector-search"
Task: backend-system-architect - "Create references/adr-best-practices.md for architecture-decision-record"
Task: ai-ml-engineer - "Create examples for design-system-starter, testing-strategy-builder, github-cli"
```

### Phase 2 (Run in parallel)
```
Task: backend-system-architect - "Create references + examples for api-design-framework, streaming-api-patterns"
Task: backend-system-architect - "Create files for evidence-verification, golden-dataset-management"
Task: ai-ml-engineer - "Create examples + checklists for langfuse, observability, performance skills"
Task: code-quality-reviewer - "Create files for brainstorming, code-review-playbook, devops-deployment"
```

### Phase 3 (Run in parallel)
```
Task: code-quality-reviewer - "Create files for quality-gates, security-checklist"
Task: frontend-ui-developer - "Create files for webapp-testing, ascii-visualizer"
Task: backend-system-architect - "Create files for database-schema-designer"
```

### Phase 4 (Run in parallel)
```
Task: frontend-ui-developer - "Full build for edge-computing-patterns"
Task: frontend-ui-developer - "Full build for type-safety-validation"
```

---

**Status:** Ready for execution
**Next Step:** Run Phase 1 with `/start-parallel` or manually launch subagents
