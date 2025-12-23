# 🛡️ NeMo Guardrails - GitHub Issue Planning

**Date:** December 22, 2025  
**Status:** Analysis Complete - Ready for Issue Creation

---

## 📊 Current Repository State Analysis

### Active Milestones (from issue data)

1. **#19: Stabilizing** (No due date)
   - Critical bug fixes for frontend/backend state synchronization
   - Issues: #456, #455, #454, #453, #442

2. **#18: 🟣 Frontend Code Health** (Due: 2026-02-18)
   - Frontend quality initiative
   - Issues: #434, #433, #409, #406, #404

3. **#17: 🔄 Langfuse Migration** (Due: 2026-01-07)
   - Migrate from LangSmith to Langfuse
   - Issues: #432, #428, #420, #416, #415, #414, #413, #412, #411, #409, #388, #382, #380

4. **#7: 🔵 Staging/Production** (Due: 2026-02-26)
   - Staging environment and production deployment readiness
   - Issues: #423, #422, #421

5. **#4: 🟡 Tutoring System** (Due: 2026-02-05)
   - Complete Socratic tutoring experience
   - Issues: #344, #343, #213

### Relevant Open Issues

**Backend + LangGraph Issues:**
- #455: verify(backend): Fail-open mechanism for low specificity research content (HIGH, Stabilizing)
- #454: bug(backend): G-Eval depth=0.0 for empty/failed agent outputs (HIGH, Stabilizing)
- #453: bug(backend): executive_summary > 500 chars schema violation (LOW, Stabilizing)
- #442: bug(backend): Quality gate fail-open allows low-quality artifacts to be marked 'complete' (HIGH, no milestone)
- #436: [Backend][MCP] Complete MCP Tool Integration for All Agents (HIGH, no milestone)

**Security/Quality Related:**
- #442: Quality gate fail-open (related to output validation - guardrails would help)
- #455: Low specificity research content (topical rails would help)

### Label Patterns

**Common Labels for Backend Features:**
- `🔵 backend` - Backend development
- `🤖 langgraph` - LangGraph workflows & agents
- `✨ feature` - New features
- `⚡ high` - High priority, sprint critical
- `🔄 medium` - Medium priority
- `🧪 testing` - Test coverage & quality
- `📊 integration` - Integration points

---

## 🎯 Suggested GitHub Issue Structure

### Option 1: Single Epic Issue (Recommended for "Dry Run")

**Create ONE main issue** that covers Phase 1 (MVP) as a "dry run" to validate the approach before committing to full implementation.

#### Issue Title:
```
feat(backend): NeMo Guardrails Integration - Phase 1 MVP (Dry Run)
```

#### Labels:
- `🔵 backend`
- `🤖 langgraph`
- `✨ feature`
- `⚡ high` (or `🔄 medium` for dry run)
- `🧪 testing`

#### Milestone:
**Create NEW milestone:** `🛡️ NeMo Guardrails Integration` (Due: 2026-01-15)

Or assign to existing milestone if there's a better fit (e.g., "Stabilizing" #19 for security/quality focus)

#### Issue Body Structure:
```markdown
## 🎯 Goal
Dry run implementation of NeMo Guardrails for analysis workflow agents to validate:
- Integration approach
- Performance impact
- False positive rate
- Configuration management

## 📋 Scope (Phase 1 MVP)
- [ ] Install NeMo Guardrails dependency
- [ ] Create guardrails service module
- [ ] Create base + analysis Colang 2.0 configs
- [ ] Integrate with model_factory.py (feature flag)
- [ ] Unit tests for guardrails wrapper
- [ ] Integration tests for analysis workflow
- [ ] Performance benchmarking
- [ ] Documentation

## 🔗 Related
- Research Plan: `docs/NEMO_GUARDRAILS_INTEGRATION_PLAN.md`
- Visual Summary: `docs/NEMO_GUARDRAILS_VISUAL_SUMMARY.md`

## ✅ Success Criteria
- Guardrails block jailbreak attempts
- No performance degradation (<300ms latency)
- <5% false positive rate
- 80%+ test coverage
- Feature flag works (can disable if issues)

## 📝 Notes
This is a dry run to validate the approach before full implementation.
If successful, will proceed with Phase 2 (Tutor workflow) and Phase 3 (Advanced features).
```

---

### Option 2: Separate Issues Per Phase (For Full Implementation)

If you want to plan all phases upfront, create separate issues:

#### Issue #1: Phase 1 MVP
- Title: `feat(backend): NeMo Guardrails - Phase 1 MVP (Analysis Workflow)`
- Milestone: `🛡️ NeMo Guardrails Integration - Phase 1`
- Due: 2026-01-15

#### Issue #2: Phase 2 Tutor
- Title: `feat(backend): NeMo Guardrails - Phase 2 (Tutor Workflow)`
- Milestone: `🛡️ NeMo Guardrails Integration - Phase 2`
- Due: 2026-01-22
- Depends on: Phase 1

#### Issue #3: Phase 3 Advanced
- Title: `feat(backend): NeMo Guardrails - Phase 3 (Advanced Features)`
- Milestone: `🛡️ NeMo Guardrails Integration - Phase 3`
- Due: 2026-02-05
- Depends on: Phase 2

---

## 🏷️ Suggested Milestones

### Option A: Single Milestone (Recommended for Dry Run)
```
Title: 🛡️ NeMo Guardrails Integration
Description: Security and quality enhancement via NVIDIA NeMo Guardrails. Phased rollout with feature flags.
Due Date: 2026-01-15 (Phase 1 MVP)
```

### Option B: Separate Milestones Per Phase
```
Milestone 1: 🛡️ NeMo Guardrails - Phase 1 MVP
- Due: 2026-01-15
- Issues: Phase 1 MVP issue

Milestone 2: 🛡️ NeMo Guardrails - Phase 2 Tutor
- Due: 2026-01-22
- Issues: Phase 2 Tutor issue

Milestone 3: 🛡️ NeMo Guardrails - Phase 3 Advanced
- Due: 2026-02-05
- Issues: Phase 3 Advanced issue
```

---

## 💡 Recommendation

**For "Dry Run One":**

1. **Create ONE issue** for Phase 1 MVP
   - Title: `feat(backend): NeMo Guardrails Integration - Phase 1 MVP (Dry Run)`
   - Labels: `🔵 backend`, `🤖 langgraph`, `✨ feature`, `🔄 medium` (since it's a dry run)
   - Milestone: Create new `🛡️ NeMo Guardrails Integration` (Due: 2026-01-15)

2. **Why ONE issue?**
   - Dry run = validate approach first
   - If successful, create Phase 2/3 issues later
   - Keeps scope focused and manageable
   - Easier to track progress

3. **Milestone Strategy:**
   - Create new milestone for guardrails work
   - OR assign to existing "Stabilizing" #19 if you want to group with other quality/security fixes
   - Separate milestone is cleaner for tracking

4. **Priority:**
   - Start with `🔄 medium` (dry run)
   - Can upgrade to `⚡ high` after validation

---

## 📝 Issue Template

```markdown
## 🎯 Goal
Dry run implementation of NeMo Guardrails for analysis workflow agents to validate integration approach, performance impact, and configuration management.

## 📋 Tasks (Phase 1 MVP)

### Setup
- [ ] Install `nemoguardrails` dependency
- [ ] Create `backend/app/shared/services/guardrails/` module
  - [ ] `__init__.py`
  - [ ] `config_loader.py` - Load Colang 2.0 configs
  - [ ] `rails_wrapper.py` - RunnableRails wrapper

### Configuration
- [ ] Create `backend/config/guardrails/` directory
- [ ] Create `base.co` - Shared safety rules (jailbreak detection, PII)
- [ ] Create `analysis.co` - Analysis workflow rails (input/output, topical)

### Integration
- [ ] Add `ENABLE_GUARDRAILS` feature flag to `backend/app/core/config.py`
- [ ] Modify `backend/app/core/model_factory.py` to wrap LLM with guardrails
- [ ] Add domain parameter to `get_chat_model()` for config selection

### Testing
- [ ] Unit tests: `backend/tests/unit/services/guardrails/test_rails_wrapper.py`
  - [ ] Test jailbreak detection
  - [ ] Test legitimate request passthrough
  - [ ] Test config loading
- [ ] Integration tests: Analysis workflow with guardrails enabled
- [ ] Performance benchmarks (latency measurement)

### Documentation
- [ ] Update `docs/ARCHITECTURE.md` with guardrails integration
- [ ] Add guardrails config examples to docs

## 🔗 Related Documentation
- Research Plan: `docs/NEMO_GUARDRAILS_INTEGRATION_PLAN.md`
- Visual Summary: `docs/NEMO_GUARDRAILS_VISUAL_SUMMARY.md`

## ✅ Success Criteria
- [ ] Guardrails block jailbreak attempts (tested)
- [ ] No performance degradation (<300ms additional latency)
- [ ] <5% false positive rate (legitimate requests pass)
- [ ] 80%+ test coverage for guardrails module
- [ ] Feature flag works (can disable if issues arise)
- [ ] Documentation updated

## 📊 Metrics to Track
- Guardrails latency (p50, p95, p99)
- Violation rate (jailbreak attempts blocked)
- False positive rate
- LLM call latency with/without guardrails

## 🚀 Next Steps (After Dry Run)
If successful:
- Create Phase 2 issue (Tutor workflow guardrails)
- Create Phase 3 issue (Advanced features: monitoring, tool security)
- Plan production rollout strategy

## 📝 Notes
This is a **dry run** to validate the integration approach before committing to full implementation.
All changes should be behind the `ENABLE_GUARDRAILS` feature flag (default: disabled).
```

---

## 🎯 Final Recommendation

**Create:**
1. **ONE GitHub Issue** for Phase 1 MVP (dry run)
2. **ONE Milestone** for tracking: `🛡️ NeMo Guardrails Integration` (Due: 2026-01-15)

**Labels:**
- `🔵 backend`
- `🤖 langgraph`
- `✨ feature`
- `🔄 medium` (start with medium since it's a dry run)
- `🧪 testing`

**Why this approach:**
- ✅ Focused scope (dry run = validate first)
- ✅ Clear success criteria
- ✅ Easy to track progress
- ✅ Can expand to Phase 2/3 after validation
- ✅ Feature flag allows safe rollout

**After dry run success:**
- Create separate issues for Phase 2 and Phase 3
- Or expand the same issue with Phase 2/3 tasks

---

**Ready to create?** Use the issue template above and adjust as needed!
