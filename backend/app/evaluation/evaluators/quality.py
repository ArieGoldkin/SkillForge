"""Quality evaluators using LLM-as-judge for subjective metrics.

This module provides evaluators that use an LLM to judge output quality:
- Relevance: How relevant is the output to the input?
- Depth: How thorough and detailed is the analysis?
- Accuracy: How factually correct is the output?
- Coherence: How well-structured and clear is the output?

All evaluators are compatible with LangSmith's evaluate() method.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langsmith.schemas import Example, Run

from app.core.model_factory import get_chat_model


def create_quality_evaluator(
    aspect: str = "overall",
    judge_model: str = "gpt-4o-mini",
) -> Callable[[Run, Example], Coroutine[Any, Any, dict[str, Any]]]:
    """Create an LLM-as-judge quality evaluator.

    This factory function creates evaluators that use an LLM to judge
    subjective quality aspects of outputs.

    Args:
        aspect: Quality aspect to evaluate (relevance, depth, accuracy, coherence, overall)
        judge_model: Model to use as judge (default: gpt-4o-mini for cost-effectiveness)

    Returns:
        Evaluator function compatible with LangSmith

    Example:
        ```python
        relevance_evaluator = create_quality_evaluator("relevance")
        depth_evaluator = create_quality_evaluator("depth", judge_model="gpt-5-mini")
        ```

    """
    # Define prompts for different aspects
    prompts = {
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

    prompt_template = prompts.get(aspect, prompts["overall"])

    async def quality_evaluator(run: Run, example: Example) -> dict[str, Any]:
        """Evaluate output quality using LLM-as-judge.

        Args:
            run: LangSmith run with outputs
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

        # Build prompt
        prompt_vars = {
            "input": str(inputs),
            "output": str(outputs),
            "reference": str(reference),
        }

        prompt = ChatPromptTemplate.from_template(prompt_template)

        # Get judge model
        try:
            judge = get_chat_model()
            # Override with judge model
            from app.core.config import settings

            original_model = settings.LLM_MODEL
            settings.LLM_MODEL = judge_model

            # Invoke judge
            response = await judge.ainvoke(prompt.format(**prompt_vars))

            # Restore original model
            settings.LLM_MODEL = original_model

            # Parse score - handle both string and list responses
            try:
                content = response.content
                # Handle case where content is a list (multi-part response)
                if isinstance(content, list):
                    content = str(content[0]) if content else ""
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
