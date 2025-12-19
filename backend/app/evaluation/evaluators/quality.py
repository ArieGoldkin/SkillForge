"""Quality evaluators using LLM-as-judge for subjective metrics.

This module provides evaluators that use an LLM to judge output quality:
- Relevance: How relevant is the output to the input?
- Depth: How thorough and detailed is the analysis?
- Accuracy: How factually correct is the output?
- Coherence: How well-structured and clear is the output?

All evaluators are compatible with Langfuse's evaluate() method.

Issue #299-304: Fixed dict-to-string bug where outputs were converted via str()
resulting in the LLM judge seeing "{'insights': '...'}" instead of actual content.

Issue #418: Evaluator prompts are now fetched from Langfuse via PromptManager
with automatic fallback to hardcoded prompts if Langfuse is unavailable.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.evaluation.types import Example, Run

logger = get_logger(__name__)

# Issue #299-304: Increased from 8000 to 15000 to preserve analytical depth
# Previous limit was too aggressive, causing G-Eval to see only shallow summaries,
# resulting in low depth scores (5/10). The evaluator needs sufficient context
# to properly assess depth and coherence of analysis.
MAX_CONTENT_LENGTH = 15000


def _extract_evaluable_content(data: dict[str, Any] | str | None) -> str:
    r"""Extract human-readable content from outputs/inputs for LLM evaluation.

    Issue #299-304: This fixes the critical bug where str(outputs) converted
    dicts like {"insights": "content"} to "{'insights': 'content'}" which
    the LLM judge couldn't properly evaluate.

    Args:
        data: Dictionary with analysis outputs, or string, or None

    Returns:
        Clean string content suitable for LLM judge evaluation

    Example:
        >>> _extract_evaluable_content({"insights": {"executive_summary": "Analysis..."}})
        "Executive Summary:\nAnalysis...\n\n..."

    """
    if data is None:
        return ""

    if isinstance(data, str):
        return data[:MAX_CONTENT_LENGTH]

    if not isinstance(data, dict):
        return str(data)[:MAX_CONTENT_LENGTH]

    # Priority order for content extraction
    # These are the keys that contain the actual analysis content
    content_keys = [
        "insights",
        "aggregated_insights",
        "executive_summary",
        "synthesis",
        "key_findings",
        "analysis",
        "content",
        "text",
        "output",
    ]

    # Try to find content in priority order
    extracted_parts = []

    for key in content_keys:
        if key in data:
            value = data[key]
            if isinstance(value, str) and value.strip():
                extracted_parts.append(f"{key.replace('_', ' ').title()}:\n{value}")
            elif isinstance(value, dict):
                # Recursively extract from nested dict
                nested_content = _format_nested_dict(value)
                if nested_content:
                    extracted_parts.append(nested_content)
            elif isinstance(value, list) and value:
                # Format list items
                list_content = _format_list_items(key, value)
                if list_content:
                    extracted_parts.append(list_content)

    # If we found priority content, use it
    if extracted_parts:
        content = "\n\n".join(extracted_parts)
        return content[:MAX_CONTENT_LENGTH]

    # Fallback: extract any string values from the dict
    fallback_parts = []
    for key, value in list(data.items())[:10]:  # Limit to first 10 keys
        if isinstance(value, str) and len(value) > 20:  # Skip short values
            fallback_parts.append(f"{key}: {value[:500]}")

    if fallback_parts:
        return "\n".join(fallback_parts)[:MAX_CONTENT_LENGTH]

    # Last resort: convert to string but format nicely
    return str(data)[:MAX_CONTENT_LENGTH]


def _format_nested_dict(data: dict[str, Any], depth: int = 0) -> str:
    """Format a nested dictionary into readable content.

    Args:
        data: Dictionary to format
        depth: Current nesting depth (for indentation)

    Returns:
        Formatted string representation

    """
    if depth > 2:  # Prevent infinite recursion
        return str(data)[:500]

    parts = []
    indent = "  " * depth

    for key, value in list(data.items())[:15]:  # Limit keys
        formatted_key = key.replace("_", " ").title()

        if isinstance(value, str) and value.strip():
            # Truncate long strings
            display_value = value[:1000] if len(value) > 1000 else value
            parts.append(f"{indent}{formatted_key}: {display_value}")

        elif isinstance(value, dict):
            nested = _format_nested_dict(value, depth + 1)
            if nested:
                parts.append(f"{indent}{formatted_key}:\n{nested}")

        elif isinstance(value, list) and value:
            if all(isinstance(item, str) for item in value[:5]):
                items_str = ", ".join(str(v)[:100] for v in value[:5])
                parts.append(f"{indent}{formatted_key}: {items_str}")
            elif all(isinstance(item, dict) for item in value[:3]):
                # Format list of dicts (like key_findings)
                for i, item in enumerate(value[:5]):
                    item_str = _format_nested_dict(item, depth + 1)
                    parts.append(f"{indent}{formatted_key} {i + 1}:\n{item_str}")

        elif value is not None:
            parts.append(f"{indent}{formatted_key}: {value}")

    return "\n".join(parts)


def _format_list_items(key: str, items: list) -> str:
    """Format a list of items into readable content.

    Args:
        key: The key name for context
        items: List of items to format

    Returns:
        Formatted string representation

    """
    formatted_key = key.replace("_", " ").title()
    parts = [f"{formatted_key}:"]

    for item in items[:10]:  # Limit to 10 items
        if isinstance(item, str):
            parts.append(f"  - {item[:200]}")
        elif isinstance(item, dict):
            # Extract most relevant field from dict
            summary = item.get("summary") or item.get("description") or item.get("text")
            if summary:
                parts.append(f"  - {str(summary)[:200]}")
            else:
                parts.append(f"  - {str(item)[:200]}")
        else:
            parts.append(f"  - {str(item)[:200]}")

    return "\n".join(parts)


# Hardcoded fallback prompts (used when Langfuse is unavailable)
FALLBACK_PROMPTS = {
    "relevance": """Evaluate the relevance of the output to the input.

Input: {input}
Output: {output}

Score the relevance from 0-10 where:
- 0-3: Not relevant, misses the point
- 4-6: Somewhat relevant, addresses some aspects
- 7-9: Highly relevant, addresses most aspects
- 10: Perfectly relevant, addresses all aspects

Respond with ONLY a number from 0-10.""",
    "depth": """Evaluate the depth and thoroughness of the analysis.

Input: {input}
Output: {output}

Score the depth from 0-10 where:
- 0-3: Superficial, lacks detail
- 4-6: Moderate depth, covers basics
- 7-9: Deep analysis, good detail
- 10: Extremely thorough and comprehensive

Respond with ONLY a number from 0-10.""",
    "accuracy": """Evaluate the factual accuracy of the output.

Input: {input}
Output: {output}
Reference: {reference}

Score the accuracy from 0-10 where:
- 0-3: Many errors or hallucinations
- 4-6: Some errors but mostly accurate
- 7-9: Accurate with minor issues
- 10: Completely accurate

Respond with ONLY a number from 0-10.""",
    "coherence": """Evaluate the coherence and clarity of the output.

Output: {output}

Score the coherence from 0-10 where:
- 0-3: Incoherent, confusing structure
- 4-6: Somewhat coherent, could be clearer
- 7-9: Coherent and well-structured
- 10: Perfectly clear and logical

Respond with ONLY a number from 0-10.""",
    "overall": """Evaluate the overall quality of the output.

Input: {input}
Output: {output}
Reference: {reference}

Consider relevance, depth, accuracy, and coherence.
Score the overall quality from 0-10 where:
- 0-3: Poor quality
- 4-6: Acceptable quality
- 7-9: High quality
- 10: Exceptional quality

Respond with ONLY a number from 0-10.""",
}

# Mapping from aspect to Langfuse prompt name
LANGFUSE_PROMPT_NAMES = {
    "relevance": "evaluator-quality-relevance",
    "depth": "evaluator-quality-depth",
    "accuracy": "evaluator-quality-accuracy",
    "coherence": "evaluator-quality-coherence",
    "overall": "evaluator-quality-overall",
}


async def _get_evaluator_prompt(aspect: str) -> str:
    """Get evaluator prompt from Langfuse with fallback to hardcoded.

    Issue #418: Fetches prompt from Langfuse via PromptManager for versioning
    and A/B testing. Falls back to hardcoded prompts if Langfuse is unavailable.

    Args:
        aspect: Quality aspect (relevance, depth, accuracy, coherence, overall)

    Returns:
        Prompt template string with {input}, {output}, {reference} placeholders

    """
    prompt_name = LANGFUSE_PROMPT_NAMES.get(aspect, LANGFUSE_PROMPT_NAMES["overall"])

    try:
        from app.shared.services.prompts.prompt_manager import get_prompt_manager

        prompt_manager = get_prompt_manager()
        langfuse_prompt = await prompt_manager.get_prompt(prompt_name)

        # Convert Langfuse {{variable}} syntax to ChatPromptTemplate {variable} syntax
        prompt_template = langfuse_prompt.replace("{{", "{").replace("}}", "}")

        logger.debug(
            "evaluator_prompt_fetched_from_langfuse",
            aspect=aspect,
            prompt_name=prompt_name,
        )

        return prompt_template

    except Exception as e:  # noqa: BLE001 - Graceful degradation
        logger.warning(
            "evaluator_prompt_langfuse_fallback",
            aspect=aspect,
            prompt_name=prompt_name,
            error=str(e),
            message="Using hardcoded fallback prompt",
        )
        return FALLBACK_PROMPTS.get(aspect, FALLBACK_PROMPTS["overall"])


def create_quality_evaluator(
    aspect: str = "overall",
    judge_model: str | None = None,
) -> Callable[[Run, Example], Coroutine[Any, Any, dict[str, Any]]]:
    """Create an LLM-as-judge quality evaluator.

    This factory function creates evaluators that use an LLM to judge
    subjective quality aspects of outputs.

    Issue #418: Prompts are fetched from Langfuse via PromptManager with
    automatic fallback to hardcoded prompts if unavailable.

    Args:
        aspect: Quality aspect to evaluate (relevance, depth, accuracy, coherence, overall)
        judge_model: Model to use as judge (default: settings.QUALITY_JUDGE_MODEL)

    Returns:
        Evaluator function compatible with Langfuse

    Example:
        ```python
        relevance_evaluator = create_quality_evaluator("relevance")
        depth_evaluator = create_quality_evaluator("depth", judge_model="gpt-5-mini")
        ```

    """

    async def quality_evaluator(run: Run, example: Example) -> dict[str, Any]:
        """Evaluate output quality using LLM-as-judge.

        Args:
            run: Langfuse run with outputs
            example: Golden example with inputs and reference outputs

        Returns:
            Dictionary with:
                - key: "quality_{aspect}"
                - score: Normalized score (0.0-1.0)
                - comment: Raw judge score

        """
        # Extract data
        inputs = example.inputs or {}
        outputs = run.outputs or {}
        reference = example.outputs or {}

        # Build prompt with properly extracted content (Issue #299-304)
        # Use _extract_evaluable_content instead of str() to avoid
        # sending "{'insights': '...'}" to the LLM judge
        extracted_input = _extract_evaluable_content(inputs)
        extracted_output = _extract_evaluable_content(outputs)
        extracted_reference = _extract_evaluable_content(reference)

        prompt_vars = {
            "input": extracted_input,
            "output": extracted_output,
            "reference": extracted_reference,
        }

        # Issue #299-304: Debug logging to diagnose quality score issues
        # Log content lengths to verify extraction is working
        logger.debug(
            "quality_evaluator_content_extracted",
            aspect=aspect,
            input_length=len(extracted_input),
            output_length=len(extracted_output),
            reference_length=len(extracted_reference),
            input_preview=extracted_input[:200] if extracted_input else "<empty>",
            output_preview=extracted_output[:200] if extracted_output else "<empty>",
        )

        # Issue #418: Fetch prompt from Langfuse (with fallback to hardcoded)
        prompt_template = await _get_evaluator_prompt(aspect)
        prompt = ChatPromptTemplate.from_template(prompt_template)

        # Get judge model
        try:
            # Get effective judge model from settings
            settings = get_settings()
            effective_judge_model = judge_model or settings.QUALITY_JUDGE_MODEL

            # Pass model through config so get_chat_model uses the correct provider
            judge = get_chat_model({"configurable": {"model": effective_judge_model}})

            # Invoke judge
            response = await judge.ainvoke(prompt.format(**prompt_vars))

            # Parse score - handle both string and list responses
            # Gemini returns: [{'type': 'text', 'text': '10', 'extras': {...}}]
            try:
                content = response.content
                # Handle Gemini's new multi-part dict format
                if isinstance(content, list) and content:
                    first_item = content[0]
                    if isinstance(first_item, dict):
                        # Gemini format: {'type': 'text', 'text': '10', ...}
                        content = str(first_item.get("text", first_item))
                    else:
                        content = str(first_item)
                raw_score = float(str(content).strip())
                # Normalize to 0-1
                normalized_score = raw_score / 10.0
            except (ValueError, IndexError):
                # Failed to parse score
                return {
                    "key": f"quality_{aspect}",
                    "score": 0.0,
                    "comment": f"Failed to parse judge response: {response.content}",
                }

            return {
                "key": f"quality_{aspect}",
                "score": normalized_score,
                "comment": f"{raw_score}/10",
            }

        except Exception as e:
            return {
                "key": f"quality_{aspect}",
                "score": 0.0,
                "comment": f"Judge evaluation failed: {e!s}",
            }

    return quality_evaluator


# Pre-configured evaluators for common use cases
relevance_evaluator = create_quality_evaluator("relevance")
depth_evaluator = create_quality_evaluator("depth")
accuracy_evaluator = create_quality_evaluator("accuracy")
coherence_evaluator = create_quality_evaluator("coherence")
overall_quality_evaluator = create_quality_evaluator("overall")
