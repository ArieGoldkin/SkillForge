---
name: llm-judge-validation
description: LLM-as-judge quality validation patterns
version: 1.0.0
tags: [quality-gates, llm, validation, evaluation]
size: atomic
domain: process
---

# LLM-as-Judge Validation

## Quality Aspects

```python
QUALITY_ASPECTS = [
    "relevance",    # How relevant to input?
    "depth",        # How thorough?
    "coherence",    # How well-structured?
    "accuracy",     # Are facts correct?
    "completeness"  # All sections present?
]
```

## Quality Gate Pattern

```python
async def quality_gate_node(state: WorkflowState) -> dict:
    """Validate output quality using LLM-as-judge."""
    THRESHOLD = 0.7  # 0.0-1.0
    MAX_RETRIES = 2

    if not state.get("output"):
        return {"quality_gate_passed": True}

    scores = {}
    for aspect in QUALITY_ASPECTS:
        try:
            async with asyncio.timeout(30):
                score = await evaluate_aspect(
                    input_content=state["input"],
                    output_content=state["output"],
                    aspect=aspect
                )
                scores[aspect] = score
        except TimeoutError:
            scores[aspect] = 0.7  # Fail open

    avg_score = sum(scores.values()) / len(scores) if scores else 0.0
    retry_count = state.get("retry_count", 0)
    gate_passed = avg_score >= THRESHOLD or retry_count >= MAX_RETRIES

    return {
        "quality_scores": scores,
        "quality_gate_passed": gate_passed,
        "quality_gate_retry_count": retry_count
    }
```

## Retry Logic

```python
def should_retry_synthesis(state: WorkflowState) -> str:
    if state.get("quality_gate_passed", True):
        return "continue"

    retry_count = state.get("quality_gate_retry_count", 0)
    if retry_count < MAX_RETRIES:
        return "retry_synthesis"

    return "continue"  # Max retries reached, fail open
```

## Fail-Open vs Fail-Closed

**Fail-Open (Recommended):**
- If validation fails/errors, allow workflow to continue
- Log failure for monitoring
- Use when partial output better than no output

**Fail-Closed (Critical paths):**
- Block workflow if validation fails
- Use for payment processing, security operations

## Graceful Degradation

```python
async def safe_quality_evaluation(state: dict) -> dict:
    try:
        async with asyncio.timeout(60):
            return await quality_gate_node(state)
    except TimeoutError:
        logger.warning("quality_gate_timeout")
        return {"quality_gate_passed": True}  # Fail open
    except Exception as e:
        logger.error("quality_gate_error", error=str(e))
        return {"quality_gate_passed": True}
```
