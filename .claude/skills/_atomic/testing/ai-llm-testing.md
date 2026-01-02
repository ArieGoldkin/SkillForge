---
name: ai-llm-testing
description: Testing patterns for AI/LLM applications
version: 1.0.0
tags: [testing, ai, llm, ml]
size: atomic
domain: testing
---

# AI/LLM Testing Patterns

## Challenges

- Non-deterministic outputs
- Slow API calls
- Cost per test
- Structured output validation

## Async Timeout Testing

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_llm_call_respects_timeout():
    """Ensure LLM calls honor timeout limits."""
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.1):
            await slow_llm_call()

@pytest.mark.asyncio
async def test_graceful_degradation_on_timeout():
    """Test fail-open behavior."""
    result = await llm_with_fallback(timeout=0.1)
    assert result["status"] == "fallback"
    assert "timed out" in result["error"].lower()
```

## Mocking LLM Responses

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.return_value = {
        "content": "Mocked response",
        "usage": {"tokens": 100}
    }
    return mock

@pytest.mark.asyncio
async def test_synthesis_with_mocked_llm(mock_llm):
    with patch("app.llm.get_completion", mock_llm):
        result = await synthesize(input_data)

    assert result is not None
    mock_llm.assert_called_once()

# Mock streaming response
@pytest.fixture
def mock_stream():
    async def stream():
        for chunk in ["Hello", " ", "world"]:
            yield {"content": chunk}
    return stream

@pytest.mark.asyncio
async def test_streaming(mock_stream):
    with patch("app.llm.stream_completion", mock_stream):
        chunks = [c async for c in process_stream()]
    assert "".join(chunks) == "Hello world"
```

## Structured Output Validation

```python
from pydantic import ValidationError

def test_llm_output_validates():
    """Test that LLM output matches schema."""
    raw_output = {"question": "What is 2+2?", "answer": "4"}

    # Should not raise
    validated = QuizQuestion.model_validate(raw_output)
    assert validated.answer == "4"

def test_invalid_output_raises():
    """Test schema validation catches bad output."""
    raw_output = {"question": "Test", "answer": "invalid"}

    with pytest.raises(ValidationError) as exc:
        StrictSchema.model_validate(raw_output)

    assert "answer" in str(exc.value)
```

## Golden Dataset Testing

```python
import pytest

GOLDEN_EXAMPLES = [
    {
        "input": "Summarize: The quick brown fox...",
        "expected_contains": ["fox", "quick"],
        "min_length": 10,
        "max_length": 100,
    },
]

@pytest.mark.parametrize("example", GOLDEN_EXAMPLES)
@pytest.mark.asyncio
async def test_against_golden_dataset(example):
    """Test LLM output against golden examples."""
    result = await llm_summarize(example["input"])

    # Check contains expected terms
    for term in example["expected_contains"]:
        assert term.lower() in result.lower()

    # Check length constraints
    assert len(result) >= example["min_length"]
    assert len(result) <= example["max_length"]
```

## LLM-as-Judge Testing

```python
@pytest.mark.asyncio
async def test_quality_score_normalized():
    """Quality scores should be 0.0-1.0."""
    with mock_evaluator_response(score=8):  # 8/10
        result = await evaluate_quality(sample_output)

    assert 0.0 <= result["score"] <= 1.0
    assert result["score"] == 0.8

@pytest.mark.asyncio
async def test_quality_gate_fails_below_threshold():
    """Quality gate rejects low scores."""
    with mock_scores({"relevance": 0.4, "coherence": 0.5}):
        result = await quality_gate(sample_state)

    assert result["passed"] is False
    assert result["avg_score"] < 0.7
```

## Edge Cases to Always Test

```python
@pytest.mark.parametrize("input_text", [
    "",                    # Empty
    " ",                   # Whitespace only
    "a" * 100000,          # Very long
    None,                  # Null
    "特殊字符",             # Unicode
])
@pytest.mark.asyncio
async def test_handles_edge_inputs(input_text):
    """LLM service handles edge cases gracefully."""
    result = await safe_llm_call(input_text)
    assert result is not None
    assert "error" not in result or result["handled"]
```

## Cost-Effective Testing Strategy

```python
# Unit tests: Mock LLM, run always
# Integration tests: Use VCR.py recordings
# E2E tests: Real LLM, run selectively

@pytest.mark.vcr()  # Recorded response
async def test_real_llm_response():
    result = await llm_service.complete("Hello")
    assert result is not None

@pytest.mark.llm_live  # Custom marker for real calls
@pytest.mark.skipif(os.getenv("CI"), reason="Skip live LLM in CI")
async def test_live_llm():
    result = await llm_service.complete("Hello")
    assert "hello" in result.lower()
```
