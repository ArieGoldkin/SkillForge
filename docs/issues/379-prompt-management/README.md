# Issue #379: Implement Langfuse Prompt Management

**Status:** 📋 Planned
**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** Langfuse Migration Phase 2
**Priority:** ⚡ HIGH
**Estimated Effort:** 4-6 hours (7 weeks phased rollout)
**Dependencies:** Issue #372 (Langfuse Migration) ✅ Complete

---

## Summary

Migrate all hardcoded prompts in SkillForge to **Langfuse Prompt Management** for:
- Version control without code deploys
- A/B testing different prompt versions
- Prompt playground experimentation
- Cost tracking per prompt version
- Team collaboration on prompt improvements

## Key Features

- **21 total prompts**: 10 analysis + 8 tutor + 3 synthesis
- **Managed prompts**: Store in Langfuse UI, fetch at runtime
- **Local fallback**: Continue working if Langfuse unavailable
- **Multi-level caching**: LRU (L1) + Redis (L2) + Langfuse API
- **Version tracking**: Every trace knows which prompt version was used
- **A/B testing**: Native support for prompt experiments

## Current State

### Prompt Inventory

#### Analysis Domain (10 prompts)

**Supervisor**:
1. `SUPERVISOR_PROMPT` - `supervisor_config.py`
   - Dynamic (built via `build_supervisor_prompt()`)
   - Variables: `{agent_list}`
   - Priority: **HIGH** (routing foundation)

**Agents (8 prompts)**:
2. `TECH_COMPARATOR_PROMPT` - `tech_comparator.py`
3. `SECURITY_AUDITOR_PROMPT` - `security_auditor.py`
4. `IMPLEMENTATION_PLANNER_PROMPT` - `implementation_planner.py`
5. `PERFORMANCE_ANALYST_PROMPT` - `performance_analyst.py`
6. `CODE_QUALITY_CRITIC_PROMPT` - `code_quality_critic.py`
7. `TREND_VALIDATOR_PROMPT` - `trend_validator.py`
8. `DEPENDENCY_MAPPER_PROMPT` - `dependency_mapper.py`
9. `INTEGRATION_FEASIBILITY_PROMPT` - `integration_feasibility.py`

**Synthesis (3 prompts)**:
10. `CORE_SYNTHESIS_PROMPT` - `synthesis_prompts.py`
11. `LEARNING_SYNTHESIS_PROMPT` - `synthesis_prompts.py`
12. `DOCS_SYNTHESIS_PROMPT` - `synthesis_prompts.py`

#### Tutor Domain (8 prompts)

13. `SYLLABUS_GENERATION_PROMPT` - `config.py`
14. `LESSON_DELIVERY_PROMPT` - `config.py`
15. `SOCRATIC_QUESTION_PROMPT` - `config.py`
16. `READINESS_ASSESSMENT_PROMPT` - `config.py`
17. `REPHRASE_EXPLANATION_PROMPT` - `rephrase_explain.py`
18. `REFLECTION_PROMPT` - `guide_reflection.py`
19. `SECTION_REVIEW_PROMPT` - `conduct_review.py`
20. `FINAL_CHALLENGE_PROMPT` - `final_challenge.py`

**Total**: 21 prompts

### What's Missing
- All prompts hardcoded in Python files
- No version control for prompts
- Can't update prompts without code deploy
- No A/B testing infrastructure
- No prompt usage analytics

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                  PROMPT MANAGEMENT ARCHITECTURE                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Application Layer                                                 │
│  ══════════════════                                                │
│  supervisor_config.py, agent files, synthesis_prompts.py           │
│       ↓                                                             │
│  prompt_manager.get_prompt(                                        │
│      name="analysis-supervisor-routing",                           │
│      variables={"agent_list": agents_str},                         │
│      label="production"                                            │
│  )                                                                 │
│       ↓                                                             │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              PromptManager (Abstraction)                 │     │
│  │  - get_prompt(name, variables, label)                    │     │
│  │  - Cache management (L1 LRU, L2 Redis)                   │     │
│  │  - Fallback handling                                      │     │
│  │  - Metrics tracking                                       │     │
│  └──────────┬───────────────────────┬──────────────────────┘     │
│             │                       │                             │
│             ▼                       ▼                             │
│  ┌──────────────────────┐  ┌────────────────────────────┐        │
│  │  Langfuse Client     │  │  Local YAML Fallback       │        │
│  │  - get_prompt()      │  │  - local/*.yaml            │        │
│  │  - compile()         │  │  - Same naming convention  │        │
│  └──────────────────────┘  └────────────────────────────┘        │
│                                                                    │
│  Caching Strategy                                                 │
│  ════════════════                                                 │
│  L1: In-Memory LRU (5 min TTL, 100 prompts)                       │
│       ↓ MISS                                                       │
│  L2: Redis Cache (15 min TTL, shared across workers)              │
│       ↓ MISS                                                       │
│  L3: Langfuse API (~100-200ms)                                    │
│       ↓ FAILURE                                                    │
│  Fallback: Local YAML (<1ms)                                      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Prompt Naming Convention

**Format**: `{domain}-{component}-{variant}`

Examples:
- `analysis-supervisor-routing` (supervisor)
- `analysis-agent-tech-comparator` (agent)
- `analysis-synthesis-core` (synthesis phase)
- `tutor-lesson-delivery` (tutor node)

**Rationale**:
- Domain prefix enables filtering/organization
- Component identifies usage context
- Variant supports A/B testing

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

**Goal**: Foundation without disrupting production

**Tasks**:
1. **Implement PromptManager class** (2 hours)
   - File: `backend/app/shared/services/prompts/prompt_manager.py`
   - Features: fetch, cache, fallback, compile
   - API: `get_prompt(name, variables, label)`

2. **Create local YAML prompt files** (2 hours)
   - Copy all 21 prompts from code to YAML
   - Location: `backend/app/shared/services/prompts/local/`
   - Format: Same naming as Langfuse prompts

3. **Add configuration** (30 min)
   - Environment variables:
     - `LANGFUSE_PROMPTS_ENABLED=false` (default)
     - `LANGFUSE_PROMPTS_CACHE_TTL=300`
     - `LANGFUSE_PROMPTS_FALLBACK_ENABLED=true`

4. **Write unit tests** (1 hour)
   - Test cache, fallback, compilation
   - File: `tests/unit/shared/services/prompts/test_prompt_manager.py`

5. **Create migration script** (1 hour)
   - File: `scripts/sync_prompts_to_langfuse.py`
   - Upload all prompts to Langfuse
   - Usage: `poetry run python scripts/sync_prompts_to_langfuse.py --execute`

**Acceptance**:
- [ ] PromptManager passes all unit tests
- [ ] Local YAML fallbacks tested in isolation
- [ ] Langfuse connection tested with test prompts

### Phase 2: Supervisor Migration (Week 2)

**Goal**: Migrate highest-impact prompt first

**Why Supervisor First**:
- Single prompt (simplest)
- High impact (affects all analyses)
- Easy rollback (single flag)
- Validates entire architecture

**Tasks**:
1. Create Langfuse prompt: `analysis-supervisor-routing`
2. Update `supervisor_config.py` to use PromptManager
3. Add feature flag: `TECHNIQUE_ENABLE_LANGFUSE_SUPERVISOR=false`
4. Deploy with flag OFF
5. Enable for 10% traffic (A/B test)
6. Monitor metrics
7. Ramp to 100%

**Success Metrics**:
- Fallback rate < 1%
- Latency increase < 50ms (P95)
- Agent selection quality maintained

### Phase 3: Agent Prompts (Weeks 3-4)

**Goal**: Migrate 8 agent prompts in batches

**Batch 1 (High Priority)**:
- `analysis-agent-implementation-planner`
- `analysis-agent-security-auditor`

**Batch 2 (Medium Priority)**:
- `analysis-agent-tech-comparator`
- `analysis-agent-performance-analyst`
- `analysis-agent-dependency-mapper`

**Batch 3 (Lower Priority)**:
- `analysis-agent-code-quality-critic`
- `analysis-agent-trend-validator`
- `analysis-agent-integration-feasibility`

**Per-Batch Process**:
1. Create Langfuse prompts
2. Update agent files
3. Deploy with 10% traffic
4. Monitor for 2 days
5. Ramp to 100%

### Phase 4: Synthesis Prompts (Week 5)

**Prompts**:
1. `analysis-synthesis-core` (most critical)
2. `analysis-synthesis-docs`
3. `analysis-synthesis-learning`

**Challenges**:
- Complex variable substitution (findings, conflicts)
- Must test thoroughly before production

### Phase 5: Tutor Prompts (Week 6)

**Prompts**: All 8 tutor prompts

**Priority**: Lower (less critical path)

### Phase 6: Optimization (Week 7)

**Tasks**:
- Enable Redis L2 cache for production
- Tune cache TTLs based on metrics
- Create A/B test: Simplified supervisor prompt
- Document prompt management workflows

## Configuration

### Environment Variables

```bash
# Langfuse Prompt Management (Issue #379)
LANGFUSE_PROMPTS_ENABLED=false  # Gradual rollout
LANGFUSE_PROMPTS_CACHE_TTL=300  # 5 minutes
LANGFUSE_PROMPTS_FALLBACK_ENABLED=true
LANGFUSE_PROMPTS_REDIS_URL=redis://localhost:6379  # Optional L2 cache

# Per-prompt feature flags (phased rollout)
TECHNIQUE_ENABLE_LANGFUSE_SUPERVISOR=false
TECHNIQUE_ENABLE_LANGFUSE_AGENTS=false
TECHNIQUE_ENABLE_LANGFUSE_SYNTHESIS=false
TECHNIQUE_ENABLE_LANGFUSE_TUTOR=false
```

## PromptManager API

```python
from app.shared.services.prompts.prompt_manager import PromptManager

prompt_manager = PromptManager()

# Fetch and compile prompt
compiled_prompt = await prompt_manager.get_prompt(
    name="analysis-supervisor-routing",
    variables={
        "agent_list": agents_str,
        "format_spec": json_schema,
    },
    label="production",  # Or "staging", "experiment-cot"
)

# Use compiled prompt
result = await model.ainvoke([{"role": "system", "content": compiled_prompt}])
```

## Local Prompt Format (YAML)

```yaml
# local/analysis-supervisor-routing.yaml
name: analysis-supervisor-routing
type: chat
version: "1.0"
variables:
  - agent_list
  - format_spec
prompt:
  - role: system
    content: |
      Analyze content and select agents. Output JSON: {{format_spec}}

      Agents:
      {{agent_list}}

      AGENT SELECTION GUIDELINES:
      ...
metadata:
  source: app/domains/analysis/workflows/nodes/supervisor_config.py
  last_sync: "2025-01-15T10:00:00Z"
```

## Trace Attribution

```python
async def get_prompt_with_trace_attribution(
    name: str,
    variables: dict,
    trace_id: str,
) -> str:
    """Fetch prompt and record version in trace."""
    prompt_obj = await prompt_manager.get_prompt_object(name, variables)

    # Record which version was used
    update_current_trace(
        metadata={
            f"prompt_{name}_version": prompt_obj.version,
            f"prompt_{name}_label": prompt_obj.label,
        }
    )

    return prompt_obj.compiled_content
```

**Benefit**: Every trace knows which prompt version, enabling A/B test analysis

## A/B Testing Workflow

**Example: Test simplified supervisor prompt**

1. **Create variant**:
```yaml
# Langfuse UI
name: analysis-supervisor-routing-simplified
label: experiment-simplified
prompt: [... simplified version ...]
```

2. **Update code**:
```python
variant = get_variant_selector().select_variant(
    analysis_id=str(analysis_id),
    technique="supervisor_prompt",
)

prompt_name = (
    "analysis-supervisor-routing-simplified"
    if variant == "treatment"
    else "analysis-supervisor-routing"
)
```

3. **Analyze results**:
- Filter traces by `prompt_*_version` metadata
- Compare quality scores, latency, cost
- Promote winning variant to production

## Implementation Checklist

### Phase 1: Infrastructure (Week 1)
- [ ] Create `PromptManager` class
- [ ] Implement caching (L1 LRU)
- [ ] Implement fallback to local YAML
- [ ] Create 21 local YAML files
- [ ] Add environment variables
- [ ] Write unit tests (>95% coverage)
- [ ] Create `sync_prompts_to_langfuse.py` script

### Phase 2: Supervisor (Week 2)
- [ ] Create Langfuse prompt
- [ ] Update `supervisor_config.py`
- [ ] Add feature flag
- [ ] Deploy with flag OFF
- [ ] Enable 10% traffic
- [ ] Monitor metrics
- [ ] Ramp to 100%

### Phases 3-6: See timeline above

## Acceptance Criteria

### Functional Requirements
- [ ] All 21 prompts migrated to Langfuse
- [ ] Prompts fetchable via PromptManager
- [ ] Variable substitution works
- [ ] Fallback to local YAML on failure
- [ ] Cache hit rate >95%
- [ ] Trace metadata includes prompt version

### Performance Requirements
- [ ] Prompt fetch latency <100ms (P95, cached)
- [ ] Fallback latency <5ms
- [ ] No increase in workflow latency (within 2%)

### Reliability Requirements
- [ ] Fallback trigger rate <1% in production
- [ ] Zero errors when Langfuse unavailable
- [ ] System continues with local prompts

### Quality Requirements
- [ ] Migration parity tests pass
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Documentation complete

## Rollback Plan

### Emergency Rollback (<5 min)
```bash
# Disable Langfuse prompts
LANGFUSE_PROMPTS_ENABLED=false

# Redeploy
kubectl set env deployment/skillforge-backend LANGFUSE_PROMPTS_ENABLED=false
kubectl rollout restart deployment/skillforge-backend
```

### Partial Rollback (Per-Domain)
```bash
# Disable just supervisor
TECHNIQUE_ENABLE_LANGFUSE_SUPERVISOR=false

# Keep agents enabled
TECHNIQUE_ENABLE_LANGFUSE_AGENTS=true
```

## Files to Create

### Core Service (NEW)
- `backend/app/shared/services/prompts/prompt_manager.py`
- `backend/app/shared/services/prompts/local/*.yaml` (21 files)

### Scripts (NEW)
- `backend/scripts/sync_prompts_to_langfuse.py`
- `backend/scripts/export_prompts_from_langfuse.py`

### Tests (NEW)
- `backend/tests/unit/shared/services/prompts/test_prompt_manager.py`
- `backend/tests/unit/shared/services/prompts/test_migration_parity.py`
- `backend/tests/integration/shared/services/prompts/test_prompt_manager_integration.py`

### Documentation (NEW)
- `backend/app/shared/services/prompts/README.md`
- `docs/guides/prompt-management.md`
- `docs/runbooks/langfuse-prompts-troubleshooting.md`
- `docs/adr/0XX-langfuse-prompt-management.md`

## Files to Modify

### Analysis Domain (10 files)
- `backend/app/domains/analysis/workflows/nodes/supervisor_config.py`
- `backend/app/domains/analysis/workflows/agents/*.py` (8 files)
- `backend/app/domains/analysis/workflows/tasks/aggregation/synthesis_prompts.py`

### Tutor Domain (9 files)
- `backend/app/domains/tutor/workflows/config.py`
- `backend/app/domains/tutor/workflows/nodes/*.py` (8 files)

### Config (1 file)
- `backend/app/core/config.py`

## Related Issues

- **#372**: Langfuse Migration (dependency, complete)
- **#378**: Session & User Tracking (uses sessions for A/B testing)
- **#383**: Token/Cost Tracking (measure prompt cost impact)

## Resources

- [Langfuse Prompt Management](https://langfuse.com/docs/prompts/get-started)
- [Langfuse Python SDK - Prompts](https://langfuse.com/docs/sdk/python/decorators)
- [A/B Testing with Langfuse](https://langfuse.com/docs/experimentation)
