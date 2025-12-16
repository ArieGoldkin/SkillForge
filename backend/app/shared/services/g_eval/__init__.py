"""G-Eval LLM-as-Judge Quality Scoring.

This module implements G-Eval (LLM-as-Judge) for evaluating
AI-generated content quality using chain-of-thought rubrics.

Reference: G-Eval paper (https://arxiv.org/abs/2303.16634)
"""

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

__all__ = [
    "SUPPORTED_CRITERIA",
    "GEvalResult",
    "g_eval_score",
    "g_eval_score_batch",
    "get_agent_rubrics",
    "get_criterion_rubric",
]
