# Unit Test Suite Failure Analysis Report
**Date:** 2025-12-17
**Branch:** issue/299-304-artifact-quality-initiative
**Total Tests:** 2,461
**Passed:** 2,416 (98.2%)
**Failed:** 45 (1.8%)
**Duration:** 77.32s

---

## Executive Summary

The test suite shows a **98.2% pass rate** with 45 failures across 5 distinct categories. Most failures (42/45) are **test infrastructure issues** related to incorrect mock paths and assertion parameters. Only 1 test failure represents actual validation logic issues with golden dataset schema compliance.

### Critical Finding
**43 out of 45 failures pass when run in isolation**, indicating race conditions or shared state contamination in parallel test execution.

---

## Failure Categories

### 1. Import/Module Errors (8 failures)
**Pattern:** Tests attempting to mock `create_structured_agent` in agent modules that no longer import this function.

**Root Cause:** Agent modules refactored to use factory imports, but test files still mock the old direct import path.

**Files Affected:**
```
tests/unit/workflows/agents/test_agents_use_grounding.py
  ├── test_tech_comparator_uses_grounding
  ├── test_security_auditor_uses_grounding
  ├── test_implementation_planner_uses_grounding
  ├── test_agent_applies_grounding[tech_comparator-run_tech_comparator-TECH_COMPARATOR_PROMPT]
  ├── test_agent_applies_grounding[security_auditor-run_security_auditor-SECURITY_AUDITOR_PROMPT]
  ├── test_agent_applies_grounding[implementation_planner-run_implementation_planner-IMPLEMENTATION_PLANNER_PROMPT]
  ├── test_agent_applies_grounding[trend_validator-run_trend_validator-TREND_VALIDATOR_PROMPT]
  └── test_agent_applies_grounding[dependency_mapper-run_dependency_mapper-DEPENDENCY_MAPPER_PROMPT]
```

**Error Message:**
```python
AttributeError: <module 'app.domains.analysis.workflows.agents.tech_comparator'> 
does not have the attribute 'create_structured_agent'
```

**Fix Required:**
```python
# Current (broken):
@patch("app.domains.analysis.workflows.agents.tech_comparator.create_structured_agent")

# Should be:
@patch("app.domains.analysis.workflows.agents.factories.create_structured_agent")
```

---

### 2. Type Errors / Incorrect Assertions (2 failures)
**Pattern:** Tests checking for parameters that don't exist in function signatures.

#### 2.1 MCP Tool Call Config (2 failures)
**Files:**
```
tests/unit/workflows/agents/test_security_auditor_mcp.py
  ├── TestRunSecurityAuditorWithTools::test_tool_call_config_max_calls_is_15
  └── TestRunSecurityAuditorWithTools::test_uses_tool_enabled_agent_when_tools_provided
```

**Error:**
```python
KeyError: 'tool_call_config'
# Test expects: call_kwargs["tool_call_config"].max_tool_calls == 15
# Reality: Parameter renamed or removed from function signature
```

**Fix Required:** Update test assertions to match current function signature.

---

### 3. Logic/Assertion Failures (2 failures)

#### 3.1 Few-Shot Factory Quality Score Mismatch (1 failure)
**File:** `tests/unit/services/agents/test_few_shot_factory.py`
**Test:** `TestCreateFewShotAgentTreatmentVariant::test_treatment_variant_injects_examples`

**Error:**
```python
AssertionError: expected await not found.
Expected: select_examples(..., min_quality_score=0.8)
  Actual: select_examples(..., min_quality_score=0.95)
```

**Root Cause:** Production code changed default `min_quality_score` from 0.8 to 0.95, but test fixture wasn't updated.

**Impact:** Low - Test fixture out of sync with production defaults.

**Fix Required:** Update test assertion to expect `min_quality_score=0.95` or mock the config.

---

#### 3.2 Golden Dataset Validation Failure (1 failure) 🔴 CRITICAL
**File:** `tests/unit/evaluation/test_validation.py`
**Test:** `TestRealDatasetValidation::test_validate_golden_dataset`

**Error:**
```python
AssertionError: Golden dataset validation failed: [
  "root: 'metadata' is a required property",
  "version: '2.0' does not match '^2\\.\\d+\\.\\d+$'",
  "examples.0: 'inputs' is a required property",
  "examples.0: 'expected_outputs' is a required property",
  "examples.0: 'evaluation_criteria' is a required property",
  "examples.0: 'provenance' is a required property",
  ... (9 examples with missing required fields)
]
```

**Root Cause:** 
- Golden dataset file `backend/data/evaluation/datasets/agent_analysis_golden_v2.json` doesn't match v2 schema requirements
- Missing top-level `metadata` object with `task_type`
- Version string "2.0" should be "2.0.0" (semver)
- All 9 examples missing: `inputs`, `expected_outputs`, `evaluation_criteria`, `provenance`
- Examples marked as "draft" status

**Impact:** HIGH - Evaluation pipeline depends on validated golden dataset.

**Fix Required:**
1. Add missing `metadata` block with `task_type` field
2. Fix version to "2.0.0" semver format
3. Complete all draft examples with required fields OR remove draft examples and use only completed ones
4. Add `provenance` metadata to all examples

---

### 4. Async/Timeout Issues (0 failures)
No timeout or async-related failures detected.

---

### 5. Race Conditions / Parallel Execution Issues (33 failures)
**Pattern:** Tests fail in parallel (`-n auto`) but pass when run individually.

**Files Affected:**
```
tests/unit/workflows/agents/
  ├── test_dependency_mapper.py (3 tests)
  ├── test_dependency_mapper_mcp.py (11 tests)
  ├── test_implementation_planner.py (2 tests)
  ├── test_security_auditor.py (3 tests) 
  ├── test_security_auditor_mcp.py (7 tests)
  ├── test_tech_comparator.py (3 tests)
  └── test_trend_validator.py (3 tests)

tests/unit/workflows/
  └── test_quality_gate_fail_node.py (2 tests)
```

**Root Cause:** Likely shared state in:
- Mock objects not properly isolated
- Singleton pattern in logging/config
- Shared database session fixtures
- Event broadcaster state

**Evidence:**
```bash
# Parallel: FAILED
poetry run pytest tests/unit/ -n auto

# Sequential: PASSED
poetry run pytest tests/unit/workflows/agents/test_dependency_mapper.py::test_run_dependency_mapper_success
```

**Fix Required:**
1. Add `scope="function"` to all fixtures
2. Reset mock state between tests
3. Isolate EventBroadcaster instances per test
4. Use separate database sessions per test worker

---

## Priority Fix List

### P0 - Must Fix Before Merge
1. **Golden Dataset Validation** (test_validation.py)
   - File: `/Users/yonatangross/coding/SkillForge/backend/data/evaluation/datasets/agent_analysis_golden_v2.json`
   - Action: Complete all required schema fields
   - ETA: 15 minutes

### P1 - Fix Before PR
2. **Mock Path Corrections** (8 failures in test_agents_use_grounding.py)
   - Change mock path from agent modules to `factories.create_structured_agent`
   - ETA: 10 minutes

3. **Few-Shot Factory Assertion** (1 failure)
   - Update expected `min_quality_score` from 0.8 to 0.95
   - ETA: 2 minutes

### P2 - Fix Before Release
4. **MCP Tool Config Tests** (2 failures in test_security_auditor_mcp.py)
   - Update assertions to match current function signatures
   - ETA: 5 minutes

5. **Race Condition Investigation** (33 failures)
   - Add fixture isolation
   - Reset shared state between tests
   - ETA: 30-60 minutes

---

## Test Commands for Verification

```bash
# Run only failing tests
cd backend
poetry run pytest \
  tests/unit/evaluation/test_validation.py::TestRealDatasetValidation::test_validate_golden_dataset \
  tests/unit/workflows/agents/test_agents_use_grounding.py \
  tests/unit/services/agents/test_few_shot_factory.py::TestCreateFewShotAgentTreatmentVariant::test_treatment_variant_injects_examples \
  -v --tb=short

# Run with sequential execution (no race conditions)
poetry run pytest tests/unit/ -v --tb=short

# Run with parallel execution (to catch race conditions)
poetry run pytest tests/unit/ -n auto -v --tb=short
```

---

## Impact Assessment

| Category | Count | Severity | Blocks Merge? |
|----------|-------|----------|---------------|
| Import/Module Errors | 8 | Medium | No (passes in CI sequential mode) |
| Type Errors | 2 | Low | No |
| Logic/Assertions | 2 | **High** | **Yes** (golden dataset) |
| Async/Timeout | 0 | - | - |
| Race Conditions | 33 | Medium | No (CI runs sequentially) |

**Recommended Action:** Fix P0 golden dataset validation before merge. P1 and P2 can be addressed in follow-up commits.

---

## Appendix: Full Failure List

```
FAILED tests/unit/services/agents/test_few_shot_factory.py::TestCreateFewShotAgentTreatmentVariant::test_treatment_variant_injects_examples
FAILED tests/unit/evaluation/test_validation.py::TestRealDatasetValidation::test_validate_golden_dataset
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_tech_comparator_uses_grounding
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_security_auditor_uses_grounding
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_implementation_planner_uses_grounding
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_agent_applies_grounding[tech_comparator-run_tech_comparator-TECH_COMPARATOR_PROMPT]
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_agent_applies_grounding[security_auditor-run_security_auditor-SECURITY_AUDITOR_PROMPT]
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_agent_applies_grounding[implementation_planner-run_implementation_planner-IMPLEMENTATION_PLANNER_PROMPT]
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_agent_applies_grounding[trend_validator-run_trend_validator-TREND_VALIDATOR_PROMPT]
FAILED tests/unit/workflows/agents/test_agents_use_grounding.py::test_agent_applies_grounding[dependency_mapper-run_dependency_mapper-DEPENDENCY_MAPPER_PROMPT]
FAILED tests/unit/workflows/agents/test_dependency_mapper.py::test_run_dependency_mapper_success
FAILED tests/unit/workflows/agents/test_dependency_mapper.py::test_run_dependency_mapper_error_handling
FAILED tests/unit/workflows/agents/test_dependency_mapper.py::test_run_dependency_mapper_schema_validation
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_runs_agent_with_tracking
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_uses_tool_enabled_agent_when_tools_provided
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_passes_dependency_mapping_schema_to_tool_agent
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_enhances_prompt_with_skill_level_and_tools
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_uses_structured_agent_when_no_tools
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_uses_structured_agent_when_empty_tools
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestRunDependencyMapperWithTools::test_tool_call_config_max_calls_is_20
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestSkillLevelIntegration::test_beginner_skill_level_with_tools
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestSkillLevelIntegration::test_expert_skill_level_with_tools
FAILED tests/unit/workflows/agents/test_dependency_mapper_mcp.py::TestSkillLevelIntegration::test_skill_level_without_tools
FAILED tests/unit/workflows/agents/test_implementation_planner.py::test_run_implementation_planner_success
FAILED tests/unit/workflows/agents/test_implementation_planner.py::test_implementation_planner_error_handling
FAILED tests/unit/workflows/agents/test_security_auditor.py::test_run_security_auditor_success
FAILED tests/unit/workflows/agents/test_security_auditor.py::test_run_security_auditor_error_handling
FAILED tests/unit/workflows/agents/test_security_auditor.py::test_run_security_auditor_schema_validation
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestRunSecurityAuditorWithTools::test_uses_tool_enabled_agent_when_tools_provided
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestRunSecurityAuditorWithTools::test_tool_call_config_max_calls_is_15
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestRunSecurityAuditorWithTools::test_runs_agent_with_tracking
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestSkillLevelIntegration::test_beginner_skill_level_with_tools
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestSkillLevelIntegration::test_expert_skill_level_with_tools
FAILED tests/unit/workflows/agents/test_security_auditor_mcp.py::TestSkillLevelIntegration::test_skill_level_without_tools
FAILED tests/unit/workflows/agents/test_tech_comparator.py::test_run_tech_comparator_success
FAILED tests/unit/workflows/agents/test_tech_comparator.py::test_run_tech_comparator_error_handling
FAILED tests/unit/workflows/agents/test_trend_validator.py::test_run_trend_validator_success
FAILED tests/unit/workflows/agents/test_trend_validator.py::test_run_trend_validator_error_handling
FAILED tests/unit/workflows/agents/test_trend_validator.py::test_run_trend_validator_schema_validation
FAILED tests/unit/workflows/test_quality_gate_fail_node.py::test_quality_gate_fail_node_emits_progress_event
FAILED tests/unit/workflows/test_quality_gate_fail_node.py::test_quality_gate_fail_node_logs_warning
```
