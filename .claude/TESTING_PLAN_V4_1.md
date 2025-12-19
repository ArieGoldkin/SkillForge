# Testing Plan for Claude Code Skills v4.1.0

**Created:** 2025-12-19
**Purpose:** Thoroughly test all 5 new skills and 4 expanded skills
**Prerequisites:** Skills ecosystem v4.1.0 committed on branch `issue/378-385-langfuse-phase2`

---

## 🎯 Testing Objectives

1. **Skill Discovery**: Verify progressive loading and capabilities.json discovery
2. **Content Quality**: Validate examples, references, and templates are accurate
3. **Agent Integration**: Test subagent activation using new skills
4. **Real-World Scenarios**: Apply skills to actual SkillForge development tasks

---

## 📋 Test Suite 1: New Skills (5 skills)

### Test 1.1: llm-caching-patterns

**Skill Path:** `.claude/skills/llm-caching-patterns/`

**Progressive Loading Test:**
```
1. Read capabilities.json (verify ~100 token budget)
2. Search for "semantic cache" capability
3. Load references/redis-setup.md
4. Verify token savings vs loading full SKILL.md
```

**Content Validation:**
- [ ] Verify 7 reference files exist and are readable
- [ ] Check templates/semantic-cache-service.py runs without syntax errors
- [ ] Validate SkillForge cost savings example ($35k→$2k)
- [ ] Confirm Redis connection patterns match SkillForge production

**Agent Integration Test:**
```
Prompt: "Help me implement semantic caching for LLM responses with Redis"
Expected: Agent should:
  1. Load llm-caching-patterns/capabilities.json
  2. Identify "semantic cache" capability
  3. Load references/redis-setup.md and templates/semantic-cache-service.py
  4. Provide implementation guidance with code examples
```

**Real-World Task:**
- Implement cache hit rate monitoring using patterns from references/observability.md
- Test with SkillForge's existing Redis connection

---

### Test 1.2: langfuse-observability

**Skill Path:** `.claude/skills/langfuse-observability/`

**Progressive Loading Test:**
```
1. Read capabilities.json
2. Search for "trace LLM calls" capability
3. Verify references to Langfuse (not LangSmith)
```

**Content Validation:**
- [ ] Verify SKILL.md mentions Langfuse throughout (no LangSmith references)
- [ ] Check Langfuse integration examples match current API (2024)
- [ ] Validate trace waterfall and cost tracking patterns

**Agent Integration Test:**
```
Prompt: "Add Langfuse observability to our content analysis workflow"
Expected: Agent should:
  1. Load langfuse-observability skill
  2. Provide @observe decorator examples
  3. Show trace metadata and cost tracking
  4. Reference SkillForge's actual Langfuse setup
```

**Real-World Task:**
- Add Langfuse tracing to a new SkillForge API endpoint
- Verify trace appears in Langfuse dashboard

---

### Test 1.3: langgraph-workflows

**Skill Path:** `.claude/skills/langgraph-workflows/`

**Progressive Loading Test:**
```
1. Read capabilities.json (verify 4 references listed)
2. Load references/supervisor-worker-pattern.md
3. Compare token usage vs full SKILL.md load
```

**Content Validation:**
- [ ] Verify 4 reference files exist (state-management, supervisor-worker, conditional-routing, checkpoints-persistence)
- [ ] Check templates/supervisor-workflow.py has valid LangGraph code
- [ ] Validate SkillForge 8-agent example matches actual workflow
- [ ] Confirm StateGraph and TypedDict patterns are LangGraph 1.0+ compatible

**Agent Integration Test:**
```
Prompt: "Explain how SkillForge's supervisor-worker pattern works"
Expected: Agent should:
  1. Load langgraph-workflows skill
  2. Reference supervisor-worker-pattern.md
  3. Show SkillForge's actual routing logic
  4. Explain state accumulation with Annotated[list, add]
```

**Real-World Task:**
- Add a new agent to SkillForge's supervisor workflow
- Test checkpointing and state persistence

---

### Test 1.4: pgvector-search

**Skill Path:** `.claude/skills/pgvector-search/`

**Progressive Loading Test:**
```
1. Read capabilities.json (verify 3 references)
2. Load references/hybrid-search-rrf.md
3. Verify RRF algorithm examples
```

**Content Validation:**
- [ ] Verify 3 reference files cover hybrid search, indexing, metadata filtering
- [ ] Check templates/chunk-repository.py has valid SQLAlchemy code
- [ ] Validate SkillForge retrieval example (91.6% pass rate, 0.777 MRR)
- [ ] Confirm HNSW parameters (m=16, ef_construction=64) match production

**Agent Integration Test:**
```
Prompt: "Optimize our hybrid search to improve retrieval quality"
Expected: Agent should:
  1. Load pgvector-search skill
  2. Reference hybrid-search-rrf.md
  3. Suggest fetch multiplier tuning (2x → 3x)
  4. Show metadata boosting factors from SkillForge
```

**Real-World Task:**
- Implement metadata boosting for section titles
- Benchmark retrieval quality improvement

---

### Test 1.5: golden-dataset-management

**Skill Path:** `.claude/skills/golden-dataset-management/`

**Progressive Loading Test:**
```
1. Read capabilities.json
2. Load templates/backup-script.py
3. Verify script is production-ready (runnable)
```

**Content Validation:**
- [ ] Verify 2 reference files explain backup/restore and validation
- [ ] Check backup-script.py syntax and imports
- [ ] Validate URL contract validation logic
- [ ] Confirm 98 analyses + 415 chunks matches SkillForge golden dataset

**Agent Integration Test:**
```
Prompt: "Create a backup script for our test dataset"
Expected: Agent should:
  1. Load golden-dataset-management skill
  2. Reference templates/backup-script.py
  3. Explain embedding regeneration strategy
  4. Show URL contract validation
```

**Real-World Task:**
- Run backup_golden_dataset.py backup command
- Verify backup file created in backend/data/
- Test restore with --replace flag

---

## 📋 Test Suite 2: Expanded Skills (4 skills)

### Test 2.1: brainstorming (156→381 lines)

**Expansion Validation:**
- [ ] Verify "When NOT to Use" section exists (new)
- [ ] Check Socratic Questioning Templates section (4 subsections)
- [ ] Validate Common Pitfalls with ❌ BAD vs ✅ GOOD examples
- [ ] Confirm Real-World SkillForge Examples (3 examples)

**Agent Integration Test:**
```
Prompt: "I want to add a new caching layer to our API"
Expected: Agent should:
  1. Activate brainstorming skill
  2. Ask Socratic questions one at a time
  3. Explore 2-3 caching alternatives
  4. Present design incrementally with validation
```

**Real-World Task:**
- Brainstorm a new SkillForge feature using the Socratic method
- Verify agent follows 3-phase process (Understanding → Exploration → Design)

---

### Test 2.2: performance-optimization (173→629 lines)

**Expansion Validation:**
- [ ] Verify Database Query Optimization Deep Dive section (N+1 detection)
- [ ] Check Advanced Caching Strategies (multi-level hierarchy)
- [ ] Validate Profiling Tools section (py-spy, Chrome DevTools)
- [ ] Confirm Real-World SkillForge Examples (4 examples with actual metrics)

**Agent Integration Test:**
```
Prompt: "Our database queries are slow, how do we optimize them?"
Expected: Agent should:
  1. Load performance-optimization skill
  2. Reference N+1 query detection examples
  3. Show EXPLAIN ANALYZE usage
  4. Provide SkillForge-specific optimizations (selectinload)
```

**Real-World Task:**
- Profile a slow SkillForge endpoint using py-spy
- Apply N+1 query fixes using selectinload pattern

---

### Test 2.3: devops-deployment (186→845 lines)

**Expansion Validation:**
- [ ] Verify CI/CD Pipeline Patterns section (branch strategy, caching)
- [ ] Check Container Optimization Deep Dive (multi-stage builds)
- [ ] Validate Kubernetes Production Patterns (health probes, PDB)
- [ ] Confirm Real-World SkillForge Examples (docker-compose.yml, GitHub Actions)

**Agent Integration Test:**
```
Prompt: "Set up CI/CD pipeline for our Python backend"
Expected: Agent should:
  1. Load devops-deployment skill
  2. Reference GitHub Actions examples
  3. Show SkillForge's actual workflow (ruff, mypy, pytest)
  4. Include caching strategy for Poetry dependencies
```

**Real-World Task:**
- Add a new CI check to SkillForge's GitHub Actions workflow
- Test multi-stage Docker build optimization

---

### Test 2.4: observability-monitoring (191→834 lines)

**Expansion Validation:**
- [ ] Verify Advanced Structured Logging section (correlation IDs)
- [ ] Check Metrics Deep Dive (cardinality management)
- [ ] Validate Distributed Tracing Patterns (span relationships)
- [ ] Confirm Real-World SkillForge Examples (Langfuse, LLM cost tracking)

**Agent Integration Test:**
```
Prompt: "Add structured logging with correlation IDs to our API"
Expected: Agent should:
  1. Load observability-monitoring skill
  2. Reference correlation ID middleware examples
  3. Show structlog configuration from SkillForge
  4. Include log sampling strategies
```

**Real-World Task:**
- Implement correlation ID tracking in SkillForge's FastAPI middleware
- Add Prometheus metrics for LLM token usage

---

## 📋 Test Suite 3: Progressive Loading System

### Test 3.1: Token Budget Validation

**For each skill:**
```python
# Measure actual token usage
discovery_tokens = count_tokens("capabilities.json")
overview_tokens = count_tokens("SKILL.md")
reference_tokens = count_tokens("references/*.md")

# Verify against declared budgets in capabilities.json
assert discovery_tokens <= 150  # Budgeted: 100
assert overview_tokens <= 1000  # Budgeted: 600-800
```

**Test Skills:**
- [ ] llm-caching-patterns
- [ ] langgraph-workflows
- [ ] pgvector-search
- [ ] performance-optimization
- [ ] devops-deployment

---

### Test 3.2: Semantic Discovery

**Agent Registry Test:**
```
Prompt: "I need to reduce LLM costs"
Expected:
  1. Agent reads agent-registry.json
  2. Finds llm-caching-patterns via "can_solve_examples"
  3. Confidence score > 0.7
  4. Loads skill progressively (capabilities → references)
```

**Test Queries:**
- [ ] "Optimize database performance" → performance-optimization
- [ ] "Set up observability" → observability-monitoring, langfuse-observability
- [ ] "Implement hybrid search" → pgvector-search
- [ ] "Design workflow orchestration" → langgraph-workflows
- [ ] "Backup test data" → golden-dataset-management

---

### Test 3.3: Workflow Composition

**Pre-composed Workflows Test:**
```
Check: .claude/workflows/ai-integration.md
Expected:
  1. References llm-caching-patterns
  2. References langfuse-observability
  3. Shows composed multi-skill solution
  4. Token savings vs ad-hoc skill loading
```

---

## 📋 Test Suite 4: Integration Tests

### Test 4.1: Multi-Skill Task

**Scenario:** "Build a new LLM-powered feature with observability and caching"

**Expected Agent Behavior:**
```
1. Activate ai-native-development (RAG/LLM integration)
2. Activate llm-caching-patterns (semantic cache)
3. Activate langfuse-observability (tracing)
4. Check workflows/ai-integration.md for composed solution
5. Progressive load only needed sections
```

**Validation:**
- [ ] Agent discovers all 3 skills
- [ ] Progressive loading used (not full SKILL.md)
- [ ] Solution integrates patterns from all 3 skills
- [ ] Token usage < 3000 (vs ~8000 without progressive loading)

---

### Test 4.2: Subagent Coordination

**Scenario:** "Review and optimize our database schema"

**Expected Subagent Flow:**
```
1. backend-system-architect: Load database-schema-designer
2. backend-system-architect: Load performance-optimization
3. code-quality-reviewer: Load code-review-playbook
4. Shared context records all design decisions
```

**Validation:**
- [ ] Multiple subagents activated correctly
- [ ] Progressive loading used across subagents
- [ ] Shared context updated with decisions
- [ ] No duplicate skill loads

---

### Test 4.3: Real SkillForge Task

**Task:** Add a new analysis agent to the workflow

**Skills Expected:**
- [ ] langgraph-workflows (supervisor-worker pattern)
- [ ] testing-strategy-builder (testing the new agent)
- [ ] observability-monitoring (tracing the agent)

**Success Criteria:**
- Agent provides step-by-step implementation
- References actual SkillForge code patterns
- Tests can be run immediately
- Observability instrumentation included

---

## 📋 Test Suite 5: Regression Tests

### Test 5.1: Existing Skill Compatibility

**For each pre-existing skill:**
- [ ] Progressive loading still works
- [ ] capabilities.json format unchanged
- [ ] Agent discovery finds skills correctly

**Test Skills:**
- api-design-framework
- security-checklist
- testing-strategy-builder

---

### Test 5.2: CLAUDE.md Accuracy

**Validation:**
- [ ] Skill count shows 23 (not 18)
- [ ] Version shows 4.1.0 (not 4.0.0)
- [ ] New skills listed in table
- [ ] Expanded skills marked with "(expanded Dec 2024)"
- [ ] Release note v4.1.0 present

---

## 🎯 Success Criteria

### Must Pass (Critical):
1. ✅ All 5 new skills load without errors
2. ✅ Progressive loading saves 60%+ tokens
3. ✅ Agent discovery finds skills semantically
4. ✅ Real-world SkillForge tasks complete successfully

### Should Pass (Important):
5. ✅ Token budgets match actual usage (±20%)
6. ✅ Multi-skill tasks integrate smoothly
7. ✅ Subagent coordination works correctly
8. ✅ No regressions in existing skills

### Nice to Have (Enhancement):
9. ✅ Workflow composition tested
10. ✅ All templates runnable without modification
11. ✅ Examples match current production code

---

## 📝 Testing Checklist

**Before Starting:**
- [ ] Branch: `issue/378-385-langfuse-phase2` checked out
- [ ] Latest commit: "feat(skills): Expand Claude Code skills ecosystem to 23 modules"
- [ ] CLAUDE.md shows v4.1.0
- [ ] Progressive loading audit: 23/23 skills compliant

**Test Execution:**
- [ ] Test Suite 1: New Skills (5 tests) - ~30 min
- [ ] Test Suite 2: Expanded Skills (4 tests) - ~20 min
- [ ] Test Suite 3: Progressive Loading (3 tests) - ~15 min
- [ ] Test Suite 4: Integration Tests (3 tests) - ~25 min
- [ ] Test Suite 5: Regression Tests (2 tests) - ~10 min

**Total Estimated Time:** 100 minutes (1.5-2 hours)

---

## 🐛 Issue Reporting Template

If any test fails, document:

```markdown
**Test:** [Test Suite X.Y: Test Name]
**Skill:** [skill-name]
**Expected:** [What should happen]
**Actual:** [What actually happened]
**Error Message:** [If applicable]
**Steps to Reproduce:**
1. ...
2. ...
3. ...

**Impact:** [Critical/High/Medium/Low]
**Suggested Fix:** [If known]
```

---

## 🚀 Next Steps After Testing

1. **If all tests pass:**
   - Create PR to dev branch
   - Request code review
   - Update issue #378-385 with results

2. **If tests fail:**
   - Document failures using issue template above
   - Fix critical issues
   - Re-run failed tests
   - Update skills as needed

3. **Optional enhancements:**
   - Add more real-world examples
   - Create additional templates
   - Expand thin skills further

---

**Testing by:** [Your name]
**Date:** [Test date]
**Results:** [Link to test results document]
