# Langfuse Trace Input/Output Capture Fix

**Date**: December 21, 2025
**Issue**: Langfuse traces don't show input/output in the UI
**Status**: Fixed ✅

## Problem

Langfuse traces were created successfully for agent nodes, but the Langfuse UI showed empty input/output fields. This made debugging and observability significantly harder.

### Root Cause

The `@observe` decorator from Langfuse SDK has optional `capture_input` and `capture_output` parameters that default to `None` (not `True` as initially assumed). When these parameters are `None`, Langfuse may not properly serialize complex objects like:

- `TypedDict` (our `AnalysisState`)
- UUID objects
- Nested dictionaries with complex types
- Custom types like `AgentFinding`, `ContentRef`, etc.

## Solution

Explicitly set `capture_input=True` and `capture_output=True` on all `@observe` decorators to ensure Langfuse captures and serializes the data.

### Files Modified

#### 1. Agent Node Files (8 files)
All agent nodes in `/app/domains/analysis/workflows/nodes/agents/`:

**Previously had `@observe` decorator (3 files):**
- `tech_comparator_node.py`
- `security_auditor_node.py`
- `implementation_planner_node.py`

**Missing `@observe` decorator (5 files):**
- `code_quality_critic_node.py`
- `dependency_mapper_node.py`
- `integration_feasibility_node.py`
- `performance_analyst_node.py`
- `trend_validator_node.py`

**Change Applied:**
```python
# Before
@observe(as_type="agent", name="tech_comparator")
async def tech_comparator_node(state: AnalysisState) -> dict[str, object]:

# After
@observe(as_type="agent", name="tech_comparator", capture_input=True, capture_output=True)
async def tech_comparator_node(state: AnalysisState) -> dict[str, object]:
```

#### 2. Tracing Utility (`app/core/tracing.py`)

Updated `robust_traceable` decorator to include explicit capture flags:

```python
# Before
observed_func = observe(
    name=trace_name,
    as_type=span_type,
)(func)

# After
observed_func = observe(
    name=trace_name,
    as_type=span_type,
    capture_input=True,
    capture_output=True,
)(func)
```

## Langfuse SDK Signature

For reference, the full `@observe` decorator signature:

```python
def observe(
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    as_type: Union[
        Literal['generation', 'embedding'],
        Literal['span', 'agent', 'tool', 'chain', 'retriever', 'evaluator', 'guardrail'],
        None
    ] = None,
    capture_input: Optional[bool] = None,  # ⚠️ Defaults to None, not True!
    capture_output: Optional[bool] = None,  # ⚠️ Defaults to None, not True!
    transform_to_string: Optional[Callable[[Iterable], str]] = None
) -> Union[F, Callable[[F], F]]
```

## Verification

### Expected Behavior

After this fix, Langfuse traces should show:

**Input:**
```json
{
  "state": {
    "analysis_id": "a8c552fb-fc1f-4146-a690-7ed8f1df84db",
    "url": "https://example.com/article",
    "content_type": "article",
    "raw_content": "Test content...",
    "content_ref": {
      "uri": "analysis://a8c552fb-fc1f-4146-a690-7ed8f1df84db/content",
      "summary": "Article about...",
      "size_bytes": 5000,
      "content_type": "text/plain",
      "available_sections": ["summary", "full"]
    }
  }
}
```

**Output:**
```json
{
  "agent_findings": [
    {
      "agent_type": "tech_comparator",
      "key_insights": ["Insight 1", "Insight 2"],
      "recommendations": ["Recommendation 1"]
    }
  ]
}
```

### Testing

Run the agent node tests to verify the decorators are applied correctly:

```bash
poetry run pytest tests/unit/domains/analysis/workflows/nodes/agents/ -v
```

**Note**: There are some unrelated test failures due to UUID serialization in Redis broadcaster (separate issue).

### Manual Testing

1. Start Langfuse UI: `docker compose up -d langfuse`
2. Run an analysis: `curl -X POST http://localhost:8500/api/v1/analyses/`
3. Check Langfuse UI at `http://localhost:3000`
4. Navigate to a trace → Click on an agent span
5. Verify "Input" and "Output" tabs show the serialized data

## Related Issues

### Issue #432: Langfuse Observability Migration
This fix enhances the Langfuse migration from LangSmith by ensuring proper trace visibility.

### Known Limitations

**UUID Serialization in State:**
Langfuse automatically converts UUID objects to strings for JSON serialization. This is expected behavior.

**Large Content Truncation:**
Very large input/output may be truncated by Langfuse (configurable in Langfuse settings).

**Complex Object Serialization:**
Langfuse uses `pydantic.BaseModel.dict()` for serialization when available, falling back to `str()` for non-serializable objects.

## Future Improvements

1. **Custom Serializers**: Consider implementing `transform_to_string` parameter for custom serialization logic
2. **Sampling**: For high-volume production, add sampling to reduce trace storage costs
3. **PII Redaction**: Add automatic PII detection and redaction in captured input/output

## References

- Langfuse Python SDK Docs: https://langfuse.com/docs/sdk/python/decorators
- Langfuse Tracing Guide: https://langfuse.com/docs/tracing
- `@observe` Decorator API: https://python.reference.langfuse.com/langfuse/decorators
