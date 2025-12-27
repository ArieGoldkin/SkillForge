# Issue #564: Langfuse Prompt Observation Linking - Current Status

**Date:** December 27, 2025
**Branch:** `issue/564-566-langfuse-prompt-observations`

---

## Design Status: ✅ COMPLETE

Comprehensive design documents created:

- ✅ **[README.md](./README.md)** - Overview, plan, metrics, timeline
- ✅ **[IMPLEMENTATION_DESIGN.md](./IMPLEMENTATION_DESIGN.md)** - Detailed architecture, phases, alternatives
- ✅ **[ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)** - Visual diagrams and data flows
- ✅ **[CODE_EXAMPLES.md](./CODE_EXAMPLES.md)** - Concrete implementation examples

---

## Implementation Status: 🚧 IN PROGRESS

### ✅ Completed

**Phase 1: PromptManager Enhancement (PARTIAL)**

**File:** `backend/app/shared/services/prompts/prompt_manager.py`

Changes made:
- ✅ Added `TextPromptClient` import from langfuse
- ✅ Modified `_fetch_from_langfuse()` to store `langfuse_client` in return dict
- ✅ Removed obsolete `_record_prompt_observation()` method

**Phase 3: Invocation Layer (PARTIAL)**

**File:** `backend/app/domains/analysis/workflows/agents/invocation.py`

Changes made:
- ✅ Added `from langfuse import get_client` import
- ✅ Added prompt linking logic in `invoke_agent()`
  - Extracts `langfuse_prompt_client` from `agent.config.metadata`
  - Calls `langfuse.update_current_generation(prompt=prompt_client)`
  - Includes debug logging for linkage tracking
  - Graceful degradation on errors

### ⏳ Remaining Work

**Phase 1: PromptManager Enhancement (NEEDS COMPLETION)**

**File:** `backend/app/shared/services/prompts/prompt_manager.py`

Missing:
- ❌ **Add `get_prompt_with_langfuse_client()` method** (CRITICAL)
  - This is the main entry point for getting prompts with linkage
  - Should return `tuple[str, TextPromptClient | None]`
  - Implements L1/L2/L3/L4 cache hierarchy with client object
  - See [CODE_EXAMPLES.md](./CODE_EXAMPLES.md#example-1-promptmanager-enhancement) for implementation

**Phase 2: Agent Factory Layer (NOT STARTED)**

**Files to modify:**
1. `backend/app/domains/analysis/workflows/agents/factories.py`
   - ❌ Add `langfuse_prompt_client` parameter to `create_agent_with_optional_few_shot()`
   - ❌ Attach prompt client to agent config via `agent.with_config(metadata=...)`

2. `backend/app/domains/analysis/workflows/agents/tech_comparator.py` (pilot agent)
   - ❌ Use `get_prompt_with_langfuse_client()` instead of `get_prompt()`
   - ❌ Pass `langfuse_prompt_client` to factory

3. Repeat for other pilot agents:
   - ❌ `security_auditor.py`
   - ❌ `implementation_planner.py`

**Phase 4: Rollout (NOT STARTED)**

- ❌ Update remaining 16 agents
- ❌ Add unit tests
- ❌ Add integration tests
- ❌ Validate in dev environment

---

## Git Status

```
On branch issue/564-566-langfuse-prompt-observations

Modified files:
  - backend/app/shared/services/prompts/prompt_manager.py
  - backend/app/domains/analysis/workflows/agents/invocation.py
  - backend/app/domains/analysis/workflows/agents/factories.py (changes unknown)
  - .claude/skills/langfuse-observability/SKILL.md (changes unknown)

Untracked files:
  - docs/issues/564-langfuse-prompt-observations/ (new design docs)
```

---

## Next Immediate Steps

### Step 1: Complete PromptManager (HIGH PRIORITY)

**Add `get_prompt_with_langfuse_client()` method** to `prompt_manager.py`:

```python
async def get_prompt_with_langfuse_client(
    self,
    name: str,
    variables: dict[str, Any] | None = None,
    label: str = "production",
) -> tuple[str, Any | None]:
    """Get prompt content AND Langfuse client object for observation linking.

    Returns:
        Tuple of (compiled_prompt_string, langfuse_client_or_none)
    """
    # See CODE_EXAMPLES.md for full implementation
```

**Location:** Insert after existing `get_prompt()` method (~line 1466)

**Reference:** [CODE_EXAMPLES.md - Example 1](./CODE_EXAMPLES.md#example-1-promptmanager-enhancement)

---

### Step 2: Update Pilot Agent (tech_comparator)

**File:** `backend/app/domains/analysis/workflows/agents/tech_comparator.py`

**Change (~line 135):**

```python
# OLD:
system_prompt = await prompt_manager.get_prompt(
    name=PROMPT_NAME,
    variables={"skill_instructions": skill_instructions},
    label="production",
)

# NEW:
system_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
    name=PROMPT_NAME,
    variables={"skill_instructions": skill_instructions},
    label="production",
)
```

**Then pass to factory:**

```python
agent = await create_tech_comparator_agent_with_few_shot(
    content=content,
    system_prompt=system_prompt,
    response_schema=TechComparison,
    analysis_id=analysis_id,
    session=session,
    tools=tools,
    langfuse_prompt_client=langfuse_prompt_client,  # NEW
)
```

**Reference:** [CODE_EXAMPLES.md - Example 2](./CODE_EXAMPLES.md#example-2-agent-factory-enhancement)

---

### Step 3: Update Factory to Accept and Attach Client

**File:** `backend/app/domains/analysis/workflows/agents/factories.py`

**Modify `create_agent_with_optional_few_shot()` (~line 137):**

Add parameter:
```python
async def create_agent_with_optional_few_shot(
    ...,
    langfuse_prompt_client: Any | None = None,  # NEW
) -> Runnable:
```

Attach to agent config:
```python
# After creating agent, before returning
if langfuse_prompt_client:
    agent = agent.with_config(
        metadata={"langfuse_prompt_client": langfuse_prompt_client}
    )
```

**Reference:** [CODE_EXAMPLES.md - Example 3](./CODE_EXAMPLES.md#example-3-factory-layer-enhancement)

---

### Step 4: Test End-to-End

**Test in dev environment:**

1. Run a single analysis with `tech_comparator` agent
2. Check logs for `prompt_linked_to_generation` message
3. Go to Langfuse UI → Prompts → `analysis-agent-tech-comparator`
4. Verify **"Number of Observations" > 0**

**Expected log output:**

```
prompt_langfuse_fetched | name=analysis-agent-tech-comparator version=1
prompt_linked_to_generation | prompt_name=analysis-agent-tech-comparator agent_type=tech_comparator
```

---

### Step 5: Add Tests

**Unit tests:**
- `test_prompt_manager_langfuse_linking.py` - See [CODE_EXAMPLES.md - Example 5](./CODE_EXAMPLES.md#example-5-test-coverage)

**Integration tests:**
- `test_langfuse_prompt_linking.py` - See [CODE_EXAMPLES.md - Example 5](./CODE_EXAMPLES.md#example-5-test-coverage)

---

## Key Design Decisions

### Why Not Cache TextPromptClient?

**Considered:** Store `TextPromptClient` in L1/L2 cache for higher linkage coverage

**Rejected because:**
- `TextPromptClient` is **not serializable** (contains internal Langfuse state)
- Would need custom pickle/unpickle (fragile, version-dependent)
- Redis overhead for storing large objects
- **Trade-off:** 5-10% linkage coverage is acceptable for analytics use case

### Why Pass Client Through Execution Chain?

**Considered:** Refetch prompt from Langfuse inside `invoke_agent()`

**Rejected because:**
- **Defeats caching purpose** - adds 100-200ms to every invocation
- **Breaks separation of concerns** - invocation layer shouldn't know about prompts
- **Performance impact unacceptable**

**Chosen approach:**
- Fetch once at agent creation
- Pass through factory → execution → invocation via `agent.config.metadata`
- Link at generation span (where LLM call happens)

---

## Success Criteria

### Must Have (MVP)

- ✅ `get_prompt_with_langfuse_client()` method implemented
- ✅ Invocation layer links prompt to generation
- ✅ 3 pilot agents working (tech_comparator, security_auditor, implementation_planner)
- ✅ Langfuse UI shows observations > 0 for pilot agents
- ✅ Unit tests for new method (L1/L2/L3/L4 paths)
- ✅ Integration test for prompt linkage

### Should Have (Full Rollout)

- ⏳ All 19 agents updated
- ⏳ Observation counts > 100 per prompt after 24 hours
- ⏳ No performance regression (p95 latency < +10ms)
- ⏳ Cache hit ratio maintained (> 95%)

### Nice to Have (Analytics)

- ⏳ A/B test comparison visible in Langfuse UI
- ⏳ Prompt version performance metrics
- ⏳ Agent selection accuracy trends

---

## Risk Mitigation

| Risk | Mitigation | Status |
|------|-----------|--------|
| Performance impact | Monitor p95 latency, rollback if > +10ms | ⏳ Pending |
| Breaking changes | Extensive unit tests, gradual rollout | ⏳ Pending |
| TextPromptClient API changes | Pin langfuse SDK version | ✅ Current version: 2.x |
| Memory leaks | Profile memory in staging | ⏳ Pending |

---

## Timeline Estimate

| Phase | Duration | Status |
|-------|----------|--------|
| **Phase 1:** PromptManager | 2 days | 🔄 50% complete |
| **Phase 2:** Pilot Agents | 3 days | ⏳ Not started |
| **Phase 3:** Testing | 2 days | ⏳ Not started |
| **Phase 4:** Full Rollout | 5 days | ⏳ Not started |
| **Phase 5:** Validation | 3 days | ⏳ Not started |
| **Total** | **~2-3 weeks** | 🔄 ~10% complete |

---

## Questions for Review

1. **Should we use `get_prompt_with_langfuse_client()` for ALL agents immediately?**
   - **Recommendation:** No, start with 3 pilot agents for validation

2. **What if cache hit ratio drops below 95%?**
   - **Recommendation:** Increase L1 TTL from 5min to 10min
   - **Fallback:** Revert changes and investigate

3. **Should we track linkage coverage as a metric?**
   - **Recommendation:** Yes, add `prompt_linkage_rate` to observability

4. **What about agents that don't use PromptManager yet?**
   - **Recommendation:** Migrate to PromptManager first, then add linkage
   - **Out of scope:** Agents with hardcoded prompts (low priority)

---

## Related Documentation

- [Langfuse Prompt Management Guide](https://langfuse.com/docs/prompts)
- [Langfuse SDK Python Docs](https://langfuse.com/docs/sdk/python)
- [LangChain LCEL Chains](https://python.langchain.com/docs/expression_language/)

---

**Last Updated:** December 27, 2025
**Design Status:** ✅ Complete
**Implementation Status:** 🔄 10% complete (PromptManager partial, invocation complete)
**Next Step:** Complete `get_prompt_with_langfuse_client()` method
