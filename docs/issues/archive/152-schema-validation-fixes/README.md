# Issue #152: Add default_factory to Agent Schemas

**Status:** COMPLETE
**Sprint:** 3
**Story Points:** 1
**Assignee:** ArieGoldkin
**Completed:** November 30, 2024
**Branch:** `dev`

---

## Description

Fix Pydantic schema validation errors when LLM returns empty or null values for optional dictionary fields. The `comparison` and `compatibility` fields in agent schemas were failing validation when the LLM omitted these fields in its response.

---

## Problem

When the LLM agent returned responses without populating optional dict fields, Pydantic validation failed with errors like:

```
ValidationError: 1 validation error for TechComparison
comparison
  Field required [type=missing, input_value={...}, input_type=dict]
```

This occurred because the schema fields were defined without default values, making them implicitly required even though they were intended to be optional.

---

## Solution

Replace bare `dict` type hints with `Field(default_factory=dict)` to:
1. Make the fields truly optional with empty dict defaults
2. Avoid shared mutable default issues (Python gotcha with `default={}`)
3. Add `examples` field documentation for complex structures

---

## Tasks Completed

- [x] Add `default_factory=dict` to `TechComparison.comparison` field
- [x] Add `default_factory=dict` to `IntegrationFeasibility.compatibility` field
- [x] Add `examples` documentation for complex dict structures
- [x] Verify no validation errors occur with empty responses

---

## Acceptance Criteria

- [x] LLM responses with empty/null dict fields don't cause validation errors
- [x] Schema defaults to empty dict when field is omitted
- [x] Examples provide clear documentation for LLM prompt engineering
- [x] Existing tests continue to pass

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/workflows/agents/schemas/tech_comparator.py` | Added `default_factory=dict` to `comparison` field |
| `backend/app/workflows/agents/schemas/integration_feasibility.py` | Added `default_factory=dict` to `compatibility` field |

---

## Technical Details

### Before (Problematic)

```python
class TechComparison(BaseModel):
    comparison: dict[str, TechComparisonEntry] = Field(
        description="Comparison table..."
    )
```

This makes `comparison` a required field with no default.

### After (Fixed)

```python
class TechComparison(BaseModel):
    comparison: dict[str, TechComparisonEntry] = Field(
        default_factory=dict,
        description="Comparison table...",
        examples=[{
            "LangGraph": {
                "pros": ["Low-level control"],
                "cons": ["Steeper learning curve"],
                "use_cases": ["Long-running agents"]
            }
        }]
    )
```

This:
- Makes `comparison` optional with empty dict default
- Uses `default_factory` to avoid shared mutable default
- Provides examples for better LLM prompt engineering

### Why `default_factory` Instead of `default={}`?

```python
# BAD - shared mutable default (Python gotcha)
comparison: dict = Field(default={})

# GOOD - new dict created for each instance
comparison: dict = Field(default_factory=dict)
```

With `default={}`, all instances share the same dict object. Modifications to one instance affect all others. `default_factory=dict` creates a fresh dict for each instance.

---

## Related Issues

- **Issue #149:** GFM Template Enhancements (parent PR)
- **Issue #72:** Artifact Generation (uses these schemas)

---

## Commit

```
78aa618 fix(backend): add default_factory to agent schemas for validation resilience
```

---

*This fix ensures robust schema validation when LLM agents return partial or empty responses.*
