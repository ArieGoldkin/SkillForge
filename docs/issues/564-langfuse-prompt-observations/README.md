# Issue #564: Langfuse Prompt Observation Linking

**Status:** Design Complete
**Priority:** HIGH
**Complexity:** Medium
**Estimated Effort:** 1-3 weeks
**Date:** December 27, 2025

---

## Problem

The Langfuse Prompts UI shows **"Number of Observations: 0"** for all prompts despite active usage across the codebase. This means:

- ❌ **No prompt usage analytics** - Can't see which agents use which prompts
- ❌ **No A/B testing insights** - Can't compare prompt versions
- ❌ **No prompt performance metrics** - Can't correlate prompt changes with quality scores

### Root Cause

Current implementation uses `update_current_observation(metadata=...)` which **only adds metadata** to the current span. It does **NOT** create a proper prompt linkage that Langfuse recognizes.

**The fix:** Use `langfuse.update_current_generation(prompt=TextPromptClient)` with the actual Langfuse prompt object.

---

## Solution

Pass the Langfuse `TextPromptClient` object from prompt fetch → agent factory → LLM invocation, then link it to the generation span.

### Key Changes

1. **PromptManager Enhancement** - Add `get_prompt_with_langfuse_client()` method
2. **Agent Factories** - Accept and pass `langfuse_prompt_client` parameter
3. **Invocation Layer** - Link prompt using `update_current_generation(prompt=...)`

### Architecture

```
PromptManager (L3 fetch) → TextPromptClient object
         ↓
Agent Factory → agent.with_config(metadata={...})
         ↓
Invocation → langfuse.update_current_generation(prompt=client)
         ↓
Langfuse UI → "Number of Observations: 142" ✅
```

---

## Documentation

| File | Purpose |
|------|---------|
| **[IMPLEMENTATION_DESIGN.md](./IMPLEMENTATION_DESIGN.md)** | Complete implementation design with architecture, phases, rollout plan |
| **[ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)** | Visual diagrams of current vs proposed state, data flow, cache behavior |
| **[CODE_EXAMPLES.md](./CODE_EXAMPLES.md)** | Concrete code examples for all changes and tests |

---

## Implementation Plan

### Phase 1: PromptManager Enhancement (Week 1)

**Files:**
- `backend/app/shared/services/prompts/prompt_manager.py`

**Changes:**
- ✅ Add `get_prompt_with_langfuse_client()` method
- ✅ Modify `_fetch_from_langfuse()` to return `TextPromptClient` object
- ✅ Add unit tests (L1/L2/L3/hardcoded paths)

**Deliverables:**
- [ ] New method implemented and tested
- [ ] No regressions in existing `get_prompt()` usage
- [ ] Unit test coverage: 95%+

---

### Phase 2: Pilot Agents (Week 1-2)

**Pilot Agents (3 total):**
1. `tech_comparator.py` - High usage, well-tested
2. `security_auditor.py` - Critical path, good validation
3. `implementation_planner.py` - Common use case

**Files:**
- `backend/app/domains/analysis/workflows/agents/tech_comparator.py`
- `backend/app/domains/analysis/workflows/agents/security_auditor.py`
- `backend/app/domains/analysis/workflows/agents/implementation_planner.py`
- `backend/app/domains/analysis/workflows/agents/factories.py`

**Changes:**
- ✅ Fetch prompt with `get_prompt_with_langfuse_client()`
- ✅ Pass `langfuse_prompt_client` to factory
- ✅ Modify `create_agent_with_optional_few_shot()` to accept and attach client

**Deliverables:**
- [ ] 3 pilot agents updated and tested
- [ ] Integration tests passing
- [ ] Dev environment validation

---

### Phase 3: Invocation Layer (Week 2)

**Files:**
- `backend/app/domains/analysis/workflows/agents/invocation.py`

**Changes:**
- ✅ Update `invoke_agent()` to link prompt if available
- ✅ Add error handling for graceful degradation
- ✅ Add debug logging for linkage tracking

**Deliverables:**
- [ ] Invocation layer updated
- [ ] Integration test for prompt linkage
- [ ] Langfuse UI validation (observation counts > 0)

---

### Phase 4: Rollout to All Agents (Week 2-3)

**Remaining Agents (16 total):**
- dependency_mapper
- trend_validator
- integration_feasibility
- performance_analyst
- code_quality_critic
- research_analyst
- freshness_checker
- alternatives_finder
- source_credibility
- fact_validator
- key_insights
- actionable
- pros_cons
- audience_fit
- deep_researcher
- community_pulse

**Deliverables:**
- [ ] All agents updated (5 agents per day)
- [ ] Full test suite passing
- [ ] No performance regressions (p95 latency < +10ms)

---

### Phase 5: Production Validation (Week 3)

**Metrics:**
- [ ] Prompt observation counts > 100 per prompt (24 hours)
- [ ] Linkage coverage > 5% (acceptable with caching)
- [ ] Cache hit ratio maintained (> 95%)
- [ ] No performance degradation (p95 latency)

**Validation:**
- [ ] Langfuse UI shows observations for all prompts
- [ ] A/B test comparison visible (version 1 vs version 2)
- [ ] Prompt analytics actionable (latency, tokens, quality)

---

## Performance Considerations

### Cache Behavior

| Cache Level | Hit Time | Linkage | Coverage |
|------------|---------|---------|----------|
| L1 (in-memory) | ~1ms | ❌ No | 95% |
| L2 (Redis) | ~5-10ms | ❌ No | 4% |
| L3 (Langfuse) | ~100-200ms | ✅ **Yes** | 1% |
| L4 (hardcoded) | <1ms | ❌ No | <1% |

**Trade-off:** Only L3 Langfuse fetches get linkage, but this is acceptable because:
- First invocation → L3 → linkage recorded
- Cached invocations → fast path (no linkage needed)
- Prompt version changes → cache invalidation → new linkage

### Memory Overhead

- `TextPromptClient` object: ~1-2 KB per invocation
- Carried through execution chain, garbage collected after invocation
- **No persistent storage** - not serialized to database

---

## Testing

### Unit Tests

**File:** `backend/tests/unit/shared/services/prompts/test_prompt_manager_langfuse_linking.py`

- ✅ L1 cache hit returns `(content, None)`
- ✅ L2 cache hit returns `(content, None)`
- ✅ L3 Langfuse fetch returns `(content, TextPromptClient)`
- ✅ L4 hardcoded returns `(content, None)`
- ✅ Not found raises `ValueError`

### Integration Tests

**File:** `backend/tests/integration/test_langfuse_prompt_linking.py`

- ✅ Prompt linked to generation during invocation
- ✅ `update_current_generation(prompt=...)` called correctly
- ✅ Agent output returned successfully

### Manual Validation

1. Run full analysis in dev environment
2. Go to Langfuse UI → Prompts
3. Click prompt (e.g., `analysis-agent-tech-comparator`)
4. Verify **"Number of Observations" > 0**
5. Click observation → verify input/output/metrics visible

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Observation Count** | > 100 per prompt (24h) | Langfuse Prompts dashboard |
| **Linkage Coverage** | > 5% of invocations | `prompt_linkage_rate` metric |
| **Performance (p95)** | < +10ms regression | Agent execution time logs |
| **Cache Hit Ratio** | > 95% (unchanged) | PromptManager cache metrics |
| **A/B Test Visibility** | Qualitative validation | Manual Langfuse UI inspection |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Performance degradation | Low | Medium | Monitor p95 latency, rollback if > +10ms |
| TextPromptClient API changes | Low | High | Pin langfuse SDK version, test upgrades |
| Memory leaks from client objects | Very Low | Medium | Profile memory usage in staging |
| Breaking existing prompt fetching | Low | High | Extensive unit tests, gradual rollout |

---

## Related Issues

- **Issue #379:** Centralized prompt management (foundation)
- **Issue #418:** Langfuse prompt integration (enabled fetching)
- **Issue #384:** Agent graph visualization (similar linking pattern)

---

## References

- [Langfuse SDK Documentation](https://langfuse.com/docs/sdk/python)
- [Langfuse Prompt Management Guide](https://langfuse.com/docs/prompts)
- [LangChain LCEL Documentation](https://python.langchain.com/docs/expression_language/)

---

## Next Steps

1. **Review this design** with team
2. **Create GitHub issue** (if not already created)
3. **Implement Phase 1** (PromptManager enhancement)
4. **Test with pilot agents** (tech_comparator, security_auditor, implementation_planner)
5. **Validate in Langfuse UI** (observation counts > 0)
6. **Rollout to all agents** (5 agents per day)
7. **Production validation** (24-hour monitoring)

---

**Design Status:** ✅ Complete
**Implementation Status:** ⏳ Pending
**Estimated Timeline:** 1-3 weeks
**Complexity:** Medium (isolated changes, good test coverage)
