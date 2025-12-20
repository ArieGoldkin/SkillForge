"""G-Eval LLM-as-Judge Quality Scoring.

This module implements G-Eval (LLM-as-Judge) for evaluating
AI-generated content quality using chain-of-thought rubrics.

Reference: G-Eval paper (https://arxiv.org/abs/2303.16634)

Issue #428: Added Langfuse-compatible evaluators for run_experiment() API.
"""

from app.shared.services.g_eval.cost_tracker import GEvalCostTracker
from app.shared.services.g_eval.langfuse_evaluators import (
    average_g_eval_score_evaluator,
    create_g_eval_evaluator,
    create_g_eval_overall_evaluator,
    criterion_average_evaluator,
    get_standard_evaluators,
    get_standard_run_evaluators,
    quality_threshold_evaluator,
)
from app.shared.services.g_eval.rubrics import (
    SUPPORTED_CRITERIA,
    get_agent_rubrics,
    get_criterion_rubric,
)
from app.shared.services.g_eval.scorer import (
    GEvalResult,
    g_eval_score,
    g_eval_score_batch,
)
from app.shared.services.g_eval.self_consistency import (
    SelfConsistencyResult,
    VotingDistribution,
    score_criterion_with_self_consistency,
)

__all__ = [
    "SUPPORTED_CRITERIA",
    "GEvalCostTracker",
    "GEvalResult",
    "SelfConsistencyResult",
    "VotingDistribution",
    # Langfuse-compatible evaluators - Issue #428 (sorted alphabetically)
    "average_g_eval_score_evaluator",
    "create_g_eval_evaluator",
    "create_g_eval_overall_evaluator",
    "criterion_average_evaluator",
    # Core G-Eval (sorted alphabetically)
    "g_eval_score",
    "g_eval_score_batch",
    "get_agent_rubrics",
    "get_criterion_rubric",
    "get_standard_evaluators",
    "get_standard_run_evaluators",
    "quality_threshold_evaluator",
    "score_criterion_with_self_consistency",
]
