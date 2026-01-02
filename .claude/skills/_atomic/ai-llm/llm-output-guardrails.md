---
name: llm-output-guardrails
description: Output validation and safety checks
version: 1.0.0
tags: [llm, safety, validation, guardrails, output]
size: atomic
domain: ai-llm
---

# LLM Output Guardrails

## Validation Steps

After LLM returns, validate:
1. **Schema:** Response matches expected structure
2. **Guardrails:** No toxic/harmful content
3. **Grounding:** Claims are supported by provided context
4. **No IDs:** LLM didn't hallucinate any identifiers

## Implementation

```python
from pydantic import ValidationError

async def validate_output(
    llm_output: dict,
    context_texts: list[str],
) -> ValidationResult:
    """Validate LLM output before use."""

    # 1. Schema validation
    try:
        parsed = AnalysisOutput.model_validate(llm_output)
    except ValidationError as e:
        return ValidationResult(valid=False, reason=f"Schema error: {e}")

    # 2. Guardrails (toxic content)
    if await contains_toxic_content(parsed.content):
        return ValidationResult(valid=False, reason="Toxic content detected")

    # 3. Grounding check
    if not is_grounded(parsed.content, context_texts):
        return ValidationResult(valid=False, reason="Ungrounded claims")

    # 4. No hallucinated IDs
    if contains_uuid_pattern(parsed.content):
        return ValidationResult(valid=False, reason="Hallucinated IDs")

    return ValidationResult(valid=True)
```

## Schema Validation

```python
from pydantic import BaseModel, Field

class AnalysisOutput(BaseModel):
    """Expected LLM output schema."""
    analysis: str = Field(min_length=50)
    key_concepts: list[str] = Field(min_items=1, max_items=10)
    difficulty: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    prerequisites: list[str] = Field(default_factory=list)

# Validate
try:
    result = AnalysisOutput.model_validate(llm_output)
except ValidationError as e:
    logger.error(f"Invalid LLM output: {e}")
    raise
```

## UUID Detection

```python
import re

UUID_PATTERN = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE
)

def contains_uuid_pattern(text: str) -> bool:
    """Check if text contains any UUID patterns."""
    return bool(UUID_PATTERN.search(text))

# Usage
if contains_uuid_pattern(llm_output["analysis"]):
    raise SecurityError("LLM hallucinated UUIDs in output")
```

## Grounding Check

```python
def is_grounded(output: str, context_texts: list[str]) -> bool:
    """Check if output is grounded in provided context."""
    # Simple: check key phrases appear in context
    context_combined = " ".join(context_texts).lower()

    # Extract claims from output
    claims = extract_factual_claims(output)

    for claim in claims:
        if not any(word in context_combined for word in claim.key_words):
            return False

    return True
```

## Retry Pattern

```python
MAX_RETRIES = 2

async def call_llm_with_validation(
    prompt: str,
    context_texts: list[str]
) -> dict:
    """Call LLM with validation and retry."""

    for attempt in range(MAX_RETRIES + 1):
        llm_output = await call_llm(prompt)
        validation = await validate_output(llm_output, context_texts)

        if validation.valid:
            return llm_output

        logger.warning(
            f"Attempt {attempt + 1} failed: {validation.reason}"
        )

        if attempt < MAX_RETRIES:
            # Modify prompt for retry
            prompt = add_validation_instruction(prompt, validation.reason)

    raise ValidationError(f"Failed after {MAX_RETRIES + 1} attempts")
```

## Best Practices

- **Always validate schema** with Pydantic
- **Check for hallucinated IDs** before saving
- **Verify grounding** for factual claims
- **Implement retry** for recoverable failures
- **Log validation failures** for analysis
