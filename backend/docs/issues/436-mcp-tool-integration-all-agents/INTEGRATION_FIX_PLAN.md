# Issue #436: Tier 2 Agent Integration Fix Plan

**Date:** 2025-12-24
**Status:** Awaiting Approval
**Prepared by:** Claude Code with subagent research

---

## Executive Summary

Real-world analysis verification revealed a **critical integration gap**: the 4 Tier 2 validation agents are implemented but **never invoked** because `analysis_mode` isn't threaded through the system and supervisor doesn't filter by tier.

```
                      CURRENT STATE (BROKEN)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   API Request    ─────────►  Supervisor  ─────────►  Agents │
│   (NO mode)                  (NO tier                (OLD 8 │
│                               filtering)              only) │
│                                                             │
│   Tier 2 agents exist in code but are NEVER selected       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Research Findings

### Gap 1: Missing `analysis_mode` in API Schema

**File:** `app/domains/analysis/schemas/api.py:66-99`

```python
class AnalyzeRequest(BaseModel):
    url: HttpUrl
    analysis_id: str | None
    skill_level: Literal["beginner", "intermediate", "expert"]
    # ❌ MISSING: analysis_mode: Literal["quick", "standard", "deep_dive"]
```

### Gap 2: Missing `analysis_mode` in Workflow State

**File:** `app/domains/analysis/workflows/state.py:49-128`

```python
class AnalysisState(TypedDict, total=False):
    analysis_id: AnalysisID
    url: str
    skill_level: str
    # ❌ MISSING: analysis_mode: str
```

### Gap 3: Missing Agent Registrations

**File:** `app/core/agent_config.py`

Tier 1/2 agents partially registered:
- ✅ `key_insights`, `pros_cons`, `audience_fit`, `actionable` (Tier 1)
- ✅ `fact_validator`, `source_credibility` (Tier 2)
- ❌ `freshness_checker`, `alternatives_finder` (Tier 2) - MISSING!

### Gap 4: Supervisor Doesn't Call Tier Filter

**File:** `app/domains/analysis/workflows/nodes/supervisor.py`

The supervisor:
1. Gets agents via LLM structured output
2. Filters by content type, code patterns, content signals
3. ❌ **NEVER calls** `get_agents_for_mode()` from `registry.py`

The function exists but is orphaned:
```python
# app/domains/analysis/agents/registry.py:131-155
def get_agents_for_mode(mode: str) -> list[str]:
    """Return agent names based on analysis mode."""
    # This function is NEVER CALLED by supervisor!
```

---

## Architecture Diagram (Target State)

```
                           FIXED ARCHITECTURE
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   Frontend                                                               │
│      │                                                                   │
│      ▼                                                                   │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │ POST /api/v1/analyze                                           │     │
│   │   {                                                            │     │
│   │     "url": "https://...",                                      │     │
│   │     "skill_level": "intermediate",                             │     │
│   │     "analysis_mode": "standard"  ◄── NEW PARAMETER             │     │
│   │   }                                                            │     │
│   └───────────────────────────┬────────────────────────────────────┘     │
│                               │                                          │
│                               ▼                                          │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │ Supervisor (supervisor.py)                                     │     │
│   │                                                                │     │
│   │   1. LLM selects agents based on content                       │     │
│   │   2. Filter by content type (existing)                         │     │
│   │   3. Filter by content signals (existing)                      │     │
│   │   4. ★ NEW: Filter by tier via get_agents_for_mode()           │     │
│   │                                                                │     │
│   │   allowed_agents = get_agents_for_mode(analysis_mode)          │     │
│   │   selected_agents = [a for a in llm_selected if a in allowed]  │     │
│   │                                                                │     │
│   └───────────────────────────┬────────────────────────────────────┘     │
│                               │                                          │
│           ┌───────────────────┼───────────────────┐                      │
│           ▼                   ▼                   ▼                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│   │   TIER 1     │    │   TIER 2     │    │   TIER 3     │               │
│   │  UNIVERSAL   │    │ VALIDATION   │    │  RESEARCH    │               │
│   │              │    │              │    │              │               │
│   │ key_insights │    │fact_validator│    │deep_researcher│              │
│   │ pros_cons    │    │source_cred   │    │community_pulse│              │
│   │ audience_fit │    │freshness     │    │knowledge_cur  │              │
│   │ actionable   │    │alternatives  │    │learning_path  │              │
│   │              │    │              │    │              │               │
│   │ ✅ Quick+    │    │ ✅ Standard+ │    │ ✅ Deep Only │               │
│   └──────────────┘    └──────────────┘    └──────────────┘               │
│                               │                                          │
│                               ▼                                          │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │ MCP Tool Integration                                           │     │
│   │                                                                │     │
│   │   fact_validator ────────► Tavily Search API                   │     │
│   │   alternatives_finder ───► Tavily Search API                   │     │
│   │   freshness_checker ─────► npm/PyPI APIs                       │     │
│   │   source_credibility ────► Artifact loading                    │     │
│   │                                                                │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Add `analysis_mode` to API Schema
**Files:** `app/domains/analysis/schemas/api.py`

```python
class AnalyzeRequest(BaseModel):
    url: HttpUrl
    analysis_id: str | None
    skill_level: Literal["beginner", "intermediate", "expert"] = "intermediate"
    analysis_mode: Literal["quick", "standard", "deep_dive"] = "standard"  # NEW
```

**Subagent Usage:** `backend-system-architect` for schema design

### Phase 2: Add `analysis_mode` to Workflow State
**Files:** `app/domains/analysis/workflows/state.py`

```python
class AnalysisState(TypedDict, total=False):
    # ... existing fields ...
    analysis_mode: str  # "quick" | "standard" | "deep_dive"
```

**Subagent Usage:** `backend-system-architect` for state design

### Phase 3: Register Missing Agents
**Files:** `app/core/agent_config.py`

Add missing Tier 2 agents:
```python
"freshness_checker": AgentConfig(
    agent_type="freshness_checker",
    stage_name="freshness_check",
    display_name="Freshness Check",
    description="VALIDATION: Check if technologies mentioned are current or outdated...",
),
"alternatives_finder": AgentConfig(
    agent_type="alternatives_finder",
    stage_name="alternatives_finding",
    display_name="Alternatives Finding",
    description="VALIDATION: Find alternative technologies using Tavily search...",
),
```

**Subagent Usage:** None (straightforward addition)

### Phase 4: Wire Tier Filtering in Supervisor
**Files:** `app/domains/analysis/workflows/nodes/supervisor.py`

Add tier filtering after LLM selection:
```python
from app.domains.analysis.agents.registry import get_agents_for_mode

# After LLM selects agents and content filtering...
# Add tier-based filtering:
if analysis_mode:
    allowed_for_mode = set(get_agents_for_mode(analysis_mode))
    filtered_agents = [a for a in filtered_agents if a in allowed_for_mode]
    logger.info(
        "supervisor_tier_filtered",
        analysis_id=analysis_id,
        analysis_mode=analysis_mode,
        allowed_agents=list(allowed_for_mode),
        final_agents=filtered_agents,
    )
```

**Subagent Usage:** `code-quality-reviewer` for review

### Phase 5: Add Integration Tests
**Files:** `tests/integration/domains/analysis/test_tier_routing.py` (new)

```python
@pytest.mark.asyncio
async def test_quick_mode_only_tier1_agents():
    """Quick mode should only select Tier 1 agents."""
    # Arrange: create analysis with mode="quick"
    # Act: run supervisor
    # Assert: only key_insights, pros_cons, audience_fit, actionable selected

@pytest.mark.asyncio
async def test_standard_mode_includes_tier2_agents():
    """Standard mode should include Tier 2 agents."""
    # Arrange: create analysis with mode="standard"
    # Act: run supervisor
    # Assert: fact_validator, source_credibility, etc. can be selected

@pytest.mark.asyncio
async def test_tier2_agents_use_tavily():
    """Tier 2 agents should call Tavily when enabled."""
    # Arrange: mock Tavily API
    # Act: run fact_validator
    # Assert: Tavily was called
```

**Subagent Usage:** `code-quality-reviewer` for test patterns

### Phase 6: Real-World Verification
- Run analysis with `analysis_mode="standard"`
- Verify Tier 2 agents appear in Langfuse trace
- Confirm Tavily API calls in network logs
- Validate artifact contains validation findings

---

## Test Matrix

| Test Case | Expected Behavior | Prevention |
|-----------|-------------------|------------|
| `mode=quick` | Only Tier 1 agents (4) | Unit test + integration test |
| `mode=standard` | Tier 1 + Tier 2 agents (8) | Unit test + integration test |
| `mode=deep_dive` | All tiers (12 agents) | Unit test + integration test |
| Missing mode param | Default to `standard` | Schema default validation |
| Tavily API failure | Graceful degradation | Error handling test |

---

## Claude Subagent & Skill Usage

| Phase | Subagent/Skill | Purpose |
|-------|----------------|---------|
| 1-2 | `backend-system-architect` | Schema and state design |
| 3 | Direct implementation | Simple agent registration |
| 4 | `code-quality-reviewer` | Review tier filtering logic |
| 5 | `code-quality-reviewer` | Review test patterns |
| 6 | Direct verification | Langfuse UI + API testing |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing analyses | Default `analysis_mode="standard"` maintains behavior |
| Tier 2 agent failures | Graceful degradation with error logging |
| Tavily API rate limits | Redis caching (30-min TTL) per search |
| Frontend not updated | Backend accepts omitted mode, defaults to standard |

---

## Estimated Effort

| Phase | Time | Parallelizable |
|-------|------|----------------|
| Phase 1: API Schema | 10 min | No |
| Phase 2: State | 5 min | Yes (with 1) |
| Phase 3: Agent Reg | 5 min | Yes |
| Phase 4: Supervisor | 20 min | After 1-3 |
| Phase 5: Tests | 30 min | After 4 |
| Phase 6: Verify | 15 min | After 5 |
| **Total** | ~85 min | |

---

## Approval Request

Please review and approve this plan. Upon approval, I will:

1. Execute phases 1-3 in parallel using Claude subagents
2. Execute phase 4 (dependent on 1-3)
3. Execute phase 5 (tests)
4. Execute phase 6 (real verification with Langfuse)

**Awaiting your approval to proceed.**
