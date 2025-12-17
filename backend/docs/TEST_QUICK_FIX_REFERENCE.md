# Quick Fix Reference - Test Failures

## P0 - Critical (Must Fix Before Merge)

### 1. Golden Dataset Validation
**File:** `/Users/yonatangross/coding/SkillForge/backend/data/evaluation/datasets/agent_analysis_golden_v2.json`
**Test:** `tests/unit/evaluation/test_validation.py:400`
**Error:** Schema validation failure - missing required fields

**Required Changes:**
```json
{
  "version": "2.0.0",  // Change from "2.0"
  "metadata": {        // Add this block
    "task_type": "agent_analysis",
    "description": "Golden examples for agent analysis evaluation"
  },
  "examples": [
    {
      "id": "67303c7b-fb2b-4c7d-b9ce-d1d483652e31",
      "inputs": { ... },              // Add
      "expected_outputs": { ... },    // Add
      "evaluation_criteria": { ... }, // Add
      "provenance": {                 // Add
        "source": "...",
        "created_at": "...",
        "quality_score": 0.95
      }
    }
    // Repeat for all 9 examples
  ]
}
```

---

## P1 - Before PR

### 2. Mock Path Corrections (8 tests)
**File:** `tests/unit/workflows/agents/test_agents_use_grounding.py`

**Lines to Fix:**
- Line 138: `test_tech_comparator_uses_grounding`
- Line ~160: `test_security_auditor_uses_grounding`
- Line ~180: `test_implementation_planner_uses_grounding`
- Line ~200+: 5 parametrized `test_agent_applies_grounding` tests

**Change:**
```python
# OLD (broken):
@patch("app.domains.analysis.workflows.agents.tech_comparator.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.security_auditor.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.implementation_planner.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.trend_validator.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.dependency_mapper.create_structured_agent")

# NEW (correct):
@patch("app.domains.analysis.workflows.agents.factories.create_structured_agent")
```

**Why:** Agent modules no longer import `create_structured_agent` directly - they use the factory module.

---

### 3. Few-Shot Factory Quality Score
**File:** `tests/unit/services/agents/test_few_shot_factory.py`
**Test:** Line 343 in `test_treatment_variant_injects_examples`

**Change:**
```python
# OLD:
mock_selector.select_examples.assert_awaited_once_with(
    content='Test content',
    agent_type='tech_comparator',
    max_examples=5,
    min_quality_score=0.8  # Wrong value
)

# NEW:
mock_selector.select_examples.assert_awaited_once_with(
    content='Test content',
    agent_type='tech_comparator',
    max_examples=5,
    min_quality_score=0.95  # Updated to match production default
)
```

---

## P2 - Before Release

### 4. MCP Tool Config Tests (2 tests)
**File:** `tests/unit/workflows/agents/test_security_auditor_mcp.py`

#### Test 1: Line 219 - `test_tool_call_config_max_calls_is_15`
**Error:** `KeyError: 'tool_call_config'`

**Investigation Needed:**
```python
# Current test expects:
assert call_kwargs["tool_call_config"].max_tool_calls == 15

# Need to check actual function signature:
# - Has parameter been renamed?
# - Has it been removed?
# - Is it now nested differently?
```

**Action:** Check `app/domains/analysis/workflows/agents/security_auditor.py` function signature and update test accordingly.

#### Test 2: Line ~180 - `test_uses_tool_enabled_agent_when_tools_provided`
**Error:** Similar - likely same root cause as above.

---

### 5. Race Conditions (33 tests)
**Root Cause:** Shared state between parallel test workers

**Files Affected:**
- `tests/unit/workflows/agents/test_dependency_mapper.py`
- `tests/unit/workflows/agents/test_dependency_mapper_mcp.py`
- `tests/unit/workflows/agents/test_implementation_planner.py`
- `tests/unit/workflows/agents/test_security_auditor.py`
- `tests/unit/workflows/agents/test_security_auditor_mcp.py`
- `tests/unit/workflows/agents/test_tech_comparator.py`
- `tests/unit/workflows/agents/test_trend_validator.py`
- `tests/unit/workflows/test_quality_gate_fail_node.py`

**Potential Fixes:**
1. Add `autouse=True, scope="function"` to setup/teardown fixtures
2. Use `@pytest.fixture(scope="function")` for all fixtures (not module/session)
3. Reset mock state in teardown:
   ```python
   @pytest.fixture(autouse=True)
   def reset_mocks():
       yield
       # Reset any module-level state
       importlib.reload(module)
   ```
4. Isolate EventBroadcaster per test
5. Use separate DB sessions per worker

**Investigation Steps:**
1. Run tests with `-n 1` to confirm they pass sequentially
2. Enable verbose logging to see shared state access
3. Use `pytest-xdist` markers to isolate state-dependent tests
4. Consider marking problematic tests with `@pytest.mark.xdist_group("sequential")`

---

## Quick Verification Commands

```bash
cd /Users/yonatangross/coding/SkillForge/backend

# P0 - Test golden dataset fix
poetry run pytest tests/unit/evaluation/test_validation.py::TestRealDatasetValidation::test_validate_golden_dataset -v

# P1 - Test mock path fixes
poetry run pytest tests/unit/workflows/agents/test_agents_use_grounding.py -v

# P1 - Test few-shot factory fix
poetry run pytest tests/unit/services/agents/test_few_shot_factory.py::TestCreateFewShotAgentTreatmentVariant::test_treatment_variant_injects_examples -v

# P2 - Test MCP fixes
poetry run pytest tests/unit/workflows/agents/test_security_auditor_mcp.py::TestRunSecurityAuditorWithTools -v

# Verify no race conditions (run sequentially)
poetry run pytest tests/unit/workflows/agents/ -v --tb=short

# Test with parallelism (should pass after fixtures fixed)
poetry run pytest tests/unit/workflows/agents/ -n auto -v --tb=short
```

---

## File Locations Summary

| Priority | File Path | Line | Issue |
|----------|-----------|------|-------|
| P0 | `backend/data/evaluation/datasets/agent_analysis_golden_v2.json` | - | Schema compliance |
| P1 | `tests/unit/workflows/agents/test_agents_use_grounding.py` | 138+ | Mock paths |
| P1 | `tests/unit/services/agents/test_few_shot_factory.py` | 343 | Assertion value |
| P2 | `tests/unit/workflows/agents/test_security_auditor_mcp.py` | 219, ~180 | KeyError |
| P2 | Multiple test files | Various | Race conditions |
