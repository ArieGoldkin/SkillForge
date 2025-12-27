# Issue #564: Langfuse Prompt Observation Linking - Architecture Diagram

**Status:** Design Complete
**Date:** December 27, 2025

---

## Current State (Before Fix)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CURRENT PROMPT FLOW (NO LINKAGE)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐   fetch prompt content only                     │
│  │ PromptManager  │                                                  │
│  └────────┬───────┘                                                  │
│           │                                                          │
│           ├─→ L1 Cache (in-memory) ─→ "Hello {name}"                │
│           ├─→ L2 Cache (Redis) ─────→ "Hello {name}"                │
│           ├─→ L3 Source (Langfuse) ─→ "Hello {name}"                │
│           └─→ Hardcoded Fallback ───→ "Hello {name}"                │
│                                                                      │
│  ┌────────────────┐                                                 │
│  │ Agent Factory  │   create agent with prompt content              │
│  └────────┬───────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌────────────────┐                                                 │
│  │ Agent Exec     │   invoke LLM with messages                      │
│  └────────┬───────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌────────────────┐                                                 │
│  │ LLM Invocation │   @observe(as_type="generation")                │
│  └────────┬───────┘                                                 │
│           │                                                          │
│           │   ❌ NO PROMPT LINKAGE                                  │
│           │   update_current_observation(metadata={...})            │
│           │   (only adds metadata, doesn't link prompt)             │
│           │                                                          │
│           ▼                                                          │
│  ┌────────────────┐                                                 │
│  │ Langfuse UI    │   "Number of Observations: 0" ❌               │
│  └────────────────┘                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Proposed State (After Fix)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEW PROMPT FLOW (WITH LINKAGE)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ PromptManager                                              │             │
│  │  get_prompt_with_langfuse_client()                         │             │
│  └────────┬───────────────────────────────────────────────────┘             │
│           │                                                                  │
│           │  Returns: (content: str, client: TextPromptClient | None)       │
│           │                                                                  │
│           ├─→ L1 Cache (in-memory) ─→ ("Hello {name}", None) ⚡ fast       │
│           │                            ✓ content    ❌ no linkage           │
│           │                                                                  │
│           ├─→ L2 Cache (Redis) ─────→ ("Hello {name}", None) ⚡ fast       │
│           │                            ✓ content    ❌ no linkage           │
│           │                                                                  │
│           ├─→ L3 Source (Langfuse) ─→ ("Hello {name}", TextPromptClient) 🔗│
│           │                            ✓ content    ✅ LINKABLE             │
│           │                                                                  │
│           └─→ Hardcoded Fallback ───→ ("Hello {name}", None) ⚡ fast       │
│                                        ✓ content    ❌ no linkage           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ Agent Factory (tech_comparator.py)                         │             │
│  │                                                             │             │
│  │  system_prompt, langfuse_prompt_client =                   │             │
│  │    await prompt_manager.get_prompt_with_langfuse_client(   │             │
│  │      name="analysis-agent-tech-comparator",                │             │
│  │      variables={"skill_instructions": "..."},              │             │
│  │    )                                                        │             │
│  │                                                             │             │
│  │  agent = create_agent(                                     │             │
│  │    system_prompt=system_prompt,                            │             │
│  │    langfuse_prompt_client=langfuse_prompt_client, ← PASS   │             │
│  │  )                                                          │             │
│  └────────┬───────────────────────────────────────────────────┘             │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ create_agent_with_optional_few_shot()                      │             │
│  │                                                             │             │
│  │  # Store prompt client in agent config                     │             │
│  │  if langfuse_prompt_client:                                │             │
│  │    agent = agent.with_config(                              │             │
│  │      metadata={"langfuse_prompt_client": langfuse_prompt_client}         │
│  │    )                                                        │             │
│  └────────┬───────────────────────────────────────────────────┘             │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ run_agent_with_tracking()                                  │             │
│  │   → invoke_agent(agent, messages, ...)                     │             │
│  └────────┬───────────────────────────────────────────────────┘             │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ @observe(as_type="generation", name="agent_llm_call")      │             │
│  │ async def invoke_agent(agent, input_messages, ...):        │             │
│  │                                                             │             │
│  │   # Extract prompt client from agent config                │             │
│  │   langfuse = get_client()                                  │             │
│  │   prompt_client = agent.config.metadata.get(               │             │
│  │     "langfuse_prompt_client"                               │             │
│  │   )                                                         │             │
│  │                                                             │             │
│  │   # Link prompt to current generation ✅ KEY STEP          │             │
│  │   if prompt_client:                                        │             │
│  │     langfuse.update_current_generation(                    │             │
│  │       prompt=prompt_client  ← TextPromptClient object      │             │
│  │     )                                                       │             │
│  │                                                             │             │
│  │   # Invoke LLM                                             │             │
│  │   result = await asyncio.wait_for(                         │             │
│  │     agent.ainvoke(input_messages),                         │             │
│  │     timeout=timeout                                        │             │
│  │   )                                                         │             │
│  │   return result                                            │             │
│  └────────┬───────────────────────────────────────────────────┘             │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ Langfuse UI                                                │             │
│  │                                                             │             │
│  │  Prompts → analysis-agent-tech-comparator                  │             │
│  │    ✅ Number of Observations: 142                          │             │
│  │    ✅ Version 1: 89 observations                           │             │
│  │    ✅ Version 2: 53 observations (A/B test)                │             │
│  │                                                             │             │
│  │  Click observation → linked generation span                │             │
│  │    ✅ Prompt name: analysis-agent-tech-comparator          │             │
│  │    ✅ Prompt version: 2                                    │             │
│  │    ✅ Variables: {"skill_instructions": "..."}             │             │
│  │    ✅ Input: analysis request                              │             │
│  │    ✅ Output: tech comparison JSON                         │             │
│  │    ✅ Latency: 3.2s                                        │             │
│  │    ✅ Tokens: 1847 in, 412 out                             │             │
│  │                                                             │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Level Caching with Prompt Linkage

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  CACHE LEVELS & LINKAGE BEHAVIOR                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Request: get_prompt_with_langfuse_client("tech-comparator", label="v2")   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ L1: In-Memory LRU Cache (100 prompts, 5 min TTL)             │          │
│  │   Key: "prompt:tech-comparator:v2"                           │          │
│  │   Hit?                                                        │          │
│  │     ✓ Yes → Return ("content", None)                         │          │
│  │              ⚡ ~1ms, ❌ no linkage                          │          │
│  │     ✗ No  → Try L2                                           │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ L2: Redis Cache (shared, 15 min TTL)                         │          │
│  │   Key: "prompt:tech-comparator:v2"                           │          │
│  │   Hit?                                                        │          │
│  │     ✓ Yes → Populate L1                                      │          │
│  │              Return ("content", None)                        │          │
│  │              ⚡ ~5-10ms, ❌ no linkage                       │          │
│  │     ✗ No  → Try L3                                           │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ L3: Langfuse API (source of truth)                           │          │
│  │   API Call: langfuse.get_prompt("tech-comparator", "v2")     │          │
│  │   Success?                                                    │          │
│  │     ✓ Yes → Populate L1 + L2 caches (content only)           │          │
│  │              Return ("content", TextPromptClient)  🔗         │          │
│  │              🐌 ~100-200ms, ✅ LINKABLE                      │          │
│  │     ✗ No  → Try L4                                           │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ L4: Hardcoded Prompts (embedded fallback)                    │          │
│  │   Lookup: HARDCODED_PROMPTS["tech-comparator"]               │          │
│  │   Found?                                                      │          │
│  │     ✓ Yes → Return ("content", None)                         │          │
│  │              ⚡ ~<1ms, ❌ no linkage, ⚠️ offline mode        │          │
│  │     ✗ No  → raise ValueError("Prompt not found")             │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Cache Hit Ratio Impact:**
- **First invocation:** L3 hit → ~100-200ms → **LINKAGE RECORDED** ✅
- **Next 5 minutes:** L1 hit → ~1ms → no linkage (acceptable)
- **Next 10 minutes:** L2 hit → ~5-10ms → no linkage (acceptable)
- **After cache expiry:** L3 hit → ~100-200ms → **LINKAGE RECORDED** ✅

**Trade-off:** Linkage coverage ~5-10% of invocations, but cache performance remains optimal.

---

## Data Flow Sequence Diagram

```
┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  ┌──────────┐
│ Workflow │  │ Agent Factory│  │ Agent Exec  │  │ Invocation │  │ Langfuse │
│  Node    │  │              │  │             │  │            │  │   API    │
└────┬─────┘  └──────┬───────┘  └──────┬──────┘  └──────┬─────┘  └─────┬────┘
     │               │                 │                │              │
     │ run_tech_     │                 │                │              │
     │ comparator()  │                 │                │              │
     ├──────────────>│                 │                │              │
     │               │                 │                │              │
     │               │ get_prompt_with_langfuse_client()│              │
     │               ├────────────────────────────────────────────────>│
     │               │                 │                │              │
     │               │        ("content", TextPromptClient) 🔗         │
     │               │<────────────────────────────────────────────────┤
     │               │                 │                │              │
     │               │ create_agent(   │                │              │
     │               │   prompt_client │                │              │
     │               │ ) ──────────────│                │              │
     │               │                 │                │              │
     │               │ agent.with_config(metadata={     │              │
     │               │   "langfuse_prompt_client": obj  │              │
     │               │ })              │                │              │
     │               │<────────────────┤                │              │
     │               │                 │                │              │
     │  return agent │                 │                │              │
     │<──────────────┤                 │                │              │
     │               │                 │                │              │
     │ run_agent_with_tracking(agent)  │                │              │
     ├─────────────────────────────────>│                │              │
     │               │                 │                │              │
     │               │                 │ invoke_agent(  │              │
     │               │                 │   agent,       │              │
     │               │                 │   messages     │              │
     │               │                 │ ) ────────────>│              │
     │               │                 │                │              │
     │               │                 │                │ @observe     │
     │               │                 │                │ (generation) │
     │               │                 │                │              │
     │               │                 │ extract prompt_client from    │
     │               │                 │ agent.config.metadata         │
     │               │                 │                │              │
     │               │                 │                │ update_      │
     │               │                 │                │ current_     │
     │               │                 │                │ generation(  │
     │               │                 │                │   prompt=obj │
     │               │                 │                │ ) ──────────>│
     │               │                 │                │              │
     │               │                 │                │   🔗 LINKED │
     │               │                 │                │<─────────────┤
     │               │                 │                │              │
     │               │                 │ agent.ainvoke( │              │
     │               │                 │   messages     │              │
     │               │                 │ )              │              │
     │               │                 │                │   LLM call   │
     │               │                 │                ├─────────────>│
     │               │                 │                │              │
     │               │                 │                │   response   │
     │               │                 │                │<─────────────┤
     │               │                 │                │              │
     │               │                 │   return result│              │
     │               │                 │<───────────────┤              │
     │               │                 │                │              │
     │               │  return findings│                │              │
     │<────────────────────────────────┤                │              │
     │               │                 │                │              │
     │               │                 │                │              │
```

---

## Langfuse UI: Before vs After

### Before Fix (Current State)

```
┌────────────────────────────────────────────────────────────────────┐
│ Langfuse Prompts Dashboard                                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Prompt: analysis-agent-tech-comparator                            │
│  ├─ Latest Version: 2                                              │
│  ├─ Created: 2025-12-15                                            │
│  ├─ Number of Observations: 0  ❌ PROBLEM                         │
│  └─ Cannot see:                                                    │
│      - Which analyses used this prompt                             │
│      - Prompt performance metrics                                  │
│      - A/B test variant comparison                                 │
│                                                                     │
│  Prompt: analysis-supervisor-routing                               │
│  ├─ Latest Version: 5                                              │
│  ├─ Created: 2025-12-10                                            │
│  ├─ Number of Observations: 0  ❌ PROBLEM                         │
│  └─ Cannot see:                                                    │
│      - Agent selection accuracy                                    │
│      - Confidence score trends                                     │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### After Fix (Proposed State)

```
┌────────────────────────────────────────────────────────────────────┐
│ Langfuse Prompts Dashboard                                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Prompt: analysis-agent-tech-comparator                            │
│  ├─ Latest Version: 2                                              │
│  ├─ Created: 2025-12-15                                            │
│  ├─ Number of Observations: 142  ✅ SUCCESS                        │
│  │                                                                  │
│  └─ Version Breakdown:                                             │
│      ├─ Version 1: 89 observations (62%)                           │
│      │   ├─ Avg Latency: 3.4s                                      │
│      │   ├─ Avg Tokens: 1823 in / 398 out                          │
│      │   └─ Quality Score: 7.2/10                                  │
│      │                                                              │
│      └─ Version 2: 53 observations (38%)  🧪 A/B Test              │
│          ├─ Avg Latency: 2.9s  ⚡ 15% faster                       │
│          ├─ Avg Tokens: 1647 in / 412 out  💰 10% cheaper          │
│          └─ Quality Score: 8.1/10  🎯 12% better                   │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────│
│                                                                     │
│  Prompt: analysis-supervisor-routing                               │
│  ├─ Latest Version: 5                                              │
│  ├─ Created: 2025-12-10                                            │
│  ├─ Number of Observations: 87  ✅ SUCCESS                         │
│  │                                                                  │
│  └─ Insights:                                                      │
│      ├─ Agent selection accuracy: 94.3%                            │
│      ├─ Avg agents selected: 4.2 (range: 3-7)                      │
│      ├─ Most common agents:                                        │
│      │   1. implementation_planner (89%)                           │
│      │   2. security_auditor (67%)                                 │
│      │   3. dependency_mapper (62%)                                │
│      └─ Confidence score: 0.87 avg                                 │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Key Improvements:**
- ✅ **Observation counts visible** → Can track prompt usage
- ✅ **Version comparison** → Can A/B test prompt changes
- ✅ **Performance metrics** → Latency, tokens, quality correlation
- ✅ **Usage patterns** → Which agents are selected most often

---

## File Structure

```
backend/
├── app/
│   ├── shared/
│   │   └── services/
│   │       └── prompts/
│   │           └── prompt_manager.py  ← Modified (Phase 1)
│   │               ├── get_prompt_with_langfuse_client()  (NEW)
│   │               └── _fetch_from_langfuse()  (MODIFIED)
│   │
│   ├── domains/
│   │   └── analysis/
│   │       └── workflows/
│   │           └── agents/
│   │               ├── factories.py  ← Modified (Phase 2.1)
│   │               │   └── create_agent_with_optional_few_shot()  (MODIFIED)
│   │               │
│   │               ├── invocation.py  ← Modified (Phase 2.3)
│   │               │   └── invoke_agent()  (MODIFIED)
│   │               │
│   │               └── tech_comparator.py  ← Modified (Phase 2.2)
│   │                   └── run_tech_comparator()  (MODIFIED)
│   │                   (+ 18 other agent files...)
│   │
│   └── core/
│       └── tracing.py  ← No changes needed
│
└── tests/
    ├── unit/
    │   └── shared/
    │       └── services/
    │           └── prompts/
    │               └── test_prompt_manager_langfuse_linking.py  (NEW)
    │
    └── integration/
        └── test_langfuse_prompt_linking.py  (NEW)
```

---

## Conclusion

This architecture provides **robust, production-ready prompt observation linking** with:

✅ **Minimal code changes** (3 files modified, ~100 LOC total)
✅ **High performance** (95%+ cache hit ratio maintained)
✅ **Graceful degradation** (works with or without Langfuse)
✅ **Comprehensive testing** (unit + integration tests)
✅ **Incremental rollout** (pilot agents → full rollout)

**Next Step:** Proceed with implementation (Week 1-3 timeline).
