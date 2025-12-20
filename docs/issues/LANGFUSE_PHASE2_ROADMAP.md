# Langfuse Phase 2 - Complete Implementation Roadmap

**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** 17 - Langfuse Migration Phase 2
**Status:** 📋 Planning Complete, Ready for Implementation
**Total Issues:** 8
**Estimated Total Effort:** 12-16 hours (HIGH priority only), 7 weeks for full rollout

---

## Executive Summary

Building on the successful Langfuse migration (#372), this phase adds production-grade observability features:
- **Session & User Tracking** - Group traces by analysis/session
- **Token/Cost Tracking** - Real visibility into LLM spending
- **Prompt Management** - Version control prompts without code deploys
- **Dataset Sync** - Experiment infrastructure
- **LLM-as-Judge** - Automated quality evaluation
- **Graph Visualization** - Visual workflow debugging

## Issue Priority Matrix

```
╔═══════════════════════════════════════════════════════════════════╗
║              LANGFUSE PHASE 2 - PRIORITY MATRIX                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  🔴 HIGH PRIORITY (Must Do - Sprint 1)                            ║
║  ═══════════════════════════════════════                          ║
║  #378  Session & User Tracking          [1-2 hrs]  ⭐ DO FIRST   ║
║        └─ Enables trace grouping                                  ║
║        └─ Foundation for analytics                                ║
║                                                                   ║
║  #383  Token/Cost Tracking              [2-3 hrs]  ⭐ DO SECOND  ║
║        └─ Fixes $0.00 cost problem                                ║
║        └─ Enables cost optimization                               ║
║                                                                   ║
║  #379  Prompt Management                [4-6 hrs]  ⭐ DO THIRD   ║
║        └─ A/B testing capability                                  ║
║        └─ No-deploy prompt updates                                ║
║        └─ 7-week phased rollout                                   ║
║                                                                   ║
║  🟡 MEDIUM PRIORITY (Should Do - Sprint 2)                        ║
║  ════════════════════════════════════════                         ║
║  #381  LLM-as-Judge Evaluators          [TBD]                    ║
║        └─ Complements local G-Eval                                ║
║        └─ Advanced analytics                                      ║
║                                                                   ║
║  #380  Dataset Sync                     [TBD]                    ║
║        └─ Experiment infrastructure                               ║
║        └─ Golden dataset tracking                                 ║
║                                                                   ║
║  #384  Graph Visualization              [1-2 hrs] 🎁 Quick Win   ║
║        └─ Visual workflow debugging                               ║
║        └─ Simple callback fix                                     ║
║                                                                   ║
║  🔵 LOW PRIORITY (Nice to Have - Future)                          ║
║  ════════════════════════════════════════                         ║
║  #382  Human Annotation Workflow        [TBD]                    ║
║        └─ Manual quality review                                   ║
║                                                                   ║
║  #385  MCP Server for Prompts           [TBD]                    ║
║        └─ Claude Code integration                                 ║
║        └─ Developer productivity                                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Recommended Implementation Sequence

### Sprint 1: Core Observability (Week 1)

**Day 1-2: Issue #378 - Session & User Tracking** ⏱️ 1-2 hours
- Simplest implementation
- No breaking changes (additive only)
- Immediate value in Langfuse UI
- Foundation for other features
- **Blockers:** None
- **Enables:** #379 (A/B testing needs sessions)

**Day 2-3: Issue #383 - Token/Cost Tracking** ⏱️ 2-3 hours
- Fixes critical visibility gap ($0.00 costs)
- 12 file changes (straightforward pattern)
- Enables cost optimization
- **Blockers:** None
- **Enables:** Cost-aware prompt testing (#379)

**Day 4-5: Issue #384 - Graph Visualization** ⏱️ 1-2 hours
- Quick win with high visibility
- Minimal code changes (callback propagation)
- Visual debugging capability
- **Blockers:** None
- **Nice synergy:** Works better with #378 (session grouping)

**End of Week 1:**
- ✅ Session grouping working
- ✅ Cost visibility restored
- ✅ Workflow graphs visible
- 🎉 Major observability improvements

### Sprint 2: Advanced Features (Weeks 2-8)

**Weeks 2-8: Issue #379 - Prompt Management** ⏱️ 7 weeks phased rollout
- Week 1: Infrastructure + local fallback
- Week 2: Supervisor migration (10% → 100%)
- Weeks 3-4: Agent prompts (3 batches)
- Week 5: Synthesis prompts
- Week 6: Tutor prompts
- Week 7: Optimization + A/B testing
- **Blockers:** None
- **Enables:** #385 (MCP server for prompts)

**Parallel to #379: Issue #380 - Dataset Sync** ⏱️ TBD
- Can start anytime after #372
- Independent of other issues
- Enhances experiment workflow
- **Blockers:** None

**Parallel to #379: Issue #381 - LLM-as-Judge** ⏱️ TBD
- Complements local G-Eval
- Non-blocking evaluation
- Advanced analytics
- **Blockers:** None
- **Synergy:** Uses #378 (sessions), #383 (cost tracking)

### Future Work (Post-Sprint 2)

**Issue #382 - Human Annotation Workflow**
- Lower priority
- Requires UI components
- Manual review process
- **Blockers:** Front-end work needed

**Issue #385 - MCP Server for Prompts**
- Lowest priority
- Developer convenience feature
- **Blockers:** Requires #379 complete

## Dependency Graph

```
#372 (Langfuse Migration) ✅ COMPLETE
  │
  ├─► #378 (Session Tracking)    ─┐
  │                                ├─► #379 (Prompt Mgmt) ─► #385 (MCP)
  ├─► #383 (Token/Cost Tracking) ─┤
  │                                └─► #381 (LLM-as-Judge)
  ├─► #384 (Graph Visualization)
  │
  ├─► #380 (Dataset Sync)
  │
  └─► #382 (Human Annotation)

LEGEND:
  ─►  Enables/Enhances
  ─┐
  ─┤  Synergies
  ─┘
```

## Effort Estimates

### By Priority

| Priority | Issues | Min Hours | Max Hours | Phased Rollout |
|----------|--------|-----------|-----------|----------------|
| 🔴 HIGH  | 3      | 7         | 11        | 7 weeks (#379) |
| 🟡 MEDIUM| 3      | 6         | 12        | 2-4 weeks      |
| 🔵 LOW   | 2      | 4         | 8         | TBD            |
| **Total**| **8**  | **17**    | **31**    | **~8 weeks**   |

### By Phase

| Phase | Description | Effort | Timeline |
|-------|-------------|--------|----------|
| **Phase 1** | Core observability (#378, #383, #384) | 4-7 hours | Week 1 |
| **Phase 2** | Prompt management foundation (#379) | 4-6 hours | Week 2 |
| **Phase 3** | Prompt rollout + experiments (#379, #380, #381) | 8-15 hours | Weeks 3-8 |
| **Phase 4** | Polish + nice-to-haves (#382, #385) | 4-8 hours | Future |

## Critical Files by Issue

### Issue #378 - Session & User Tracking
**Core Changes:**
- `backend/app/api/v1/analysis/workflow_runner.py` - Add user_id
- `backend/app/domains/analysis/workflows/nodes/agents/*.py` (8 files) - Add session context
- `backend/app/domains/tutor/workflows/nodes/*.py` (8 files) - Verify session consistency

**Impact:** 16 files modified

### Issue #383 - Token/Cost Tracking
**Core Changes:**
- `backend/app/shared/services/g_eval/scorer.py` - Add callback config
- `backend/app/domains/tutor/workflows/nodes/*.py` (8 files) - Add callback config
- `backend/app/domains/analysis/services/cost_tracking.py` (NEW) - Cost aggregation

**Impact:** 12 files modified, 1 new file

### Issue #379 - Prompt Management
**Core Changes:**
- `backend/app/shared/services/prompts/prompt_manager.py` (NEW) - Core service
- `backend/app/shared/services/prompts/local/*.yaml` (21 NEW) - Fallback prompts
- `backend/scripts/sync_prompts_to_langfuse.py` (NEW) - Migration script
- `backend/app/domains/analysis/workflows/nodes/*.py` (10 files) - Use PromptManager

**Impact:** 10 files modified, 23 new files

### Issue #384 - Graph Visualization
**Core Changes:**
- `backend/app/api/v1/analysis/workflow_runner.py` - Pass callbacks to graph.ainvoke()
- `backend/app/domains/analysis/workflows/graph_builder.py` - Add graph logging

**Impact:** 2 files modified (simplest!)

## Success Metrics

### Phase 1 Success (End of Week 1)
- [ ] 100% of traces have session_id
- [ ] 100% of traces have user_id
- [ ] Langfuse dashboard shows non-zero costs
- [ ] Workflow graphs visible in Langfuse UI
- [ ] All tests passing (≥80% coverage maintained)

### Phase 2 Success (End of Week 2)
- [ ] Supervisor prompt managed in Langfuse
- [ ] Local YAML fallback tested and working
- [ ] Cache hit rate >95%
- [ ] No production incidents from prompt management

### Phase 3 Success (End of Week 8)
- [ ] All 21 prompts in Langfuse
- [ ] A/B test completed (supervisor prompt variant)
- [ ] Dataset sync operational
- [ ] LLM-as-Judge complementing G-Eval
- [ ] Cost per analysis tracked in dashboard

## Risk Mitigation

### High-Risk Areas

**Issue #379 - Prompt Management**
- **Risk:** Production prompts broken
- **Mitigation:** Phased rollout with feature flags
- **Rollback:** <5 minutes via environment variable

**Issue #383 - Token/Cost Tracking**
- **Risk:** Callback handler performance impact
- **Mitigation:** Langfuse uses async publishing (negligible overhead)
- **Rollback:** Remove config parameter, no callback

**Issue #378 - Session & User Tracking**
- **Risk:** Very low (additive only)
- **Mitigation:** Graceful degradation if Langfuse unavailable
- **Rollback:** Not needed (no user-facing impact)

### Low-Risk Quick Wins

**Issue #384 - Graph Visualization**
- **Risk:** Minimal (just callback propagation)
- **Impact:** High (visual debugging)
- **Effort:** 1-2 hours
- **Recommendation:** Do early for morale boost

## Documentation Status

| Issue | README.md | Status | Agent |
|-------|-----------|--------|-------|
| #378  | ✅ Complete | 3,500 words | Manual |
| #383  | ✅ Complete | 3,200 words | Manual |
| #379  | ✅ Complete | 4,800 words | Manual |
| #380  | 🔄 Generating | TBD | a445751 |
| #381  | 🔄 Generating | TBD | a313292 |
| #384  | 🔄 Generating | TBD | a180de1 |
| #382  | 🔄 Generating | TBD | a724b5a |
| #385  | 🔄 Generating | TBD | a8cd0a4 |

**Parallel Agents Running:** 5/5
**Completion ETA:** ~3-5 minutes

## Next Actions

### Immediate (Today)
1. ✅ Complete all issue documentation (in progress)
2. Review agent-generated docs
3. Commit docs to branch: `issue/378-385-langfuse-phase2`
4. Create GitHub project board for milestone 17

### Week 1 Sprint Planning
1. Start with #378 (Session Tracking) - 1-2 hours
2. Move to #383 (Token/Cost Tracking) - 2-3 hours
3. Quick win: #384 (Graph Visualization) - 1-2 hours
4. End-of-week demo: Show Langfuse UI improvements

### Week 2+ Planning
1. Begin #379 (Prompt Management) infrastructure
2. Parallel: Start #380 (Dataset Sync) research
3. Parallel: Start #381 (LLM-as-Judge) integration

## References

- **Milestone 17 Issues:** [GitHub Issues](https://github.com/ArieGoldkin/SkillForge/milestone/17)
- **Langfuse Integration Gaps:** `docs/LANGFUSE_INTEGRATION_GAPS.md`
- **Issue Documentation:** `docs/issues/378-385-*/README.md`
- **Previous Migration:** Issue #372 (PR #386 merged)

---

**Last Updated:** December 19, 2025
**Maintained By:** AI Development Team
**Status:** 📋 Ready for Implementation
