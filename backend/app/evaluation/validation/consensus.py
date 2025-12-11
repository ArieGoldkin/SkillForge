"""Consensus algorithm for multi-annotator validation.

This module implements a 2/3 majority rule consensus algorithm:
- Requires ≥2 annotators per chunk-query pair
- Include: mean_score ≥ 2.0 and variance ≤ 1.0
- Exclude: mean_score < 2.0 and variance ≤ 1.0
- Review: high variance (> 1.0) indicating disagreement
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.logging import get_logger
from app.evaluation.validation.models import Annotation, ConsensusResult

logger = get_logger(__name__)


@dataclass
class ConsensusAlgorithm:
    """2/3 majority rule consensus algorithm.

    Decision rules:
    - Include: mean_score ≥ include_threshold (2.0) and variance ≤ variance_threshold (1.0)
    - Exclude: mean_score < include_threshold and variance ≤ variance_threshold
    - Review: variance > variance_threshold (annotators disagree significantly)

    Attributes:
        variance_threshold: Maximum allowed variance (default: 1.0)
        include_threshold: Minimum mean score to include chunk (default: 2.0)
        min_annotators: Minimum annotators required per item (default: 2)

    """

    variance_threshold: float = 1.0
    include_threshold: float = 2.0
    min_annotators: int = 2

    def compute_consensus(
        self, example_id: str, chunk_id: str, annotations: list[Annotation]
    ) -> ConsensusResult:
        """Compute consensus for a single chunk-query pair.

        Args:
            example_id: ID of the evaluation example (query)
            chunk_id: ID of the chunk being evaluated
            annotations: List of annotations for this pair

        Returns:
            ConsensusResult with decision and confidence

        Raises:
            ValueError: If fewer than min_annotators annotations provided

        """
        if len(annotations) < self.min_annotators:
            msg = (
                f"Need at least {self.min_annotators} annotations, "
                f"got {len(annotations)} for {example_id}/{chunk_id}"
            )
            raise ValueError(msg)

        # Extract scores
        scores = [int(ann.score) for ann in annotations]
        confidences = [ann.confidence for ann in annotations]

        # Calculate statistics
        mean_score = float(np.mean(scores))
        variance = float(np.var(scores, ddof=1)) if len(scores) > 1 else 0.0

        # Compute overall confidence (average of annotator confidences, weighted by agreement)
        if variance <= self.variance_threshold:
            # Low variance = high agreement -> higher confidence
            confidence = float(np.mean(confidences))
        else:
            # High variance = disagreement -> lower confidence
            confidence = float(np.mean(confidences) * 0.5)

        # Apply decision rules
        if variance > self.variance_threshold:
            decision: str = "review"
            requires_expert_review = True
            logger.info(
                "consensus_needs_review",
                example_id=example_id,
                chunk_id=chunk_id,
                mean_score=mean_score,
                variance=variance,
                n_annotations=len(annotations),
            )
        elif mean_score >= self.include_threshold:
            decision = "include"
            requires_expert_review = False
            logger.debug(
                "consensus_include",
                example_id=example_id,
                chunk_id=chunk_id,
                mean_score=mean_score,
                variance=variance,
            )
        else:
            decision = "exclude"
            requires_expert_review = False
            logger.debug(
                "consensus_exclude",
                example_id=example_id,
                chunk_id=chunk_id,
                mean_score=mean_score,
                variance=variance,
            )

        return ConsensusResult(
            example_id=example_id,
            chunk_id=chunk_id,
            annotations=annotations,
            mean_score=mean_score,
            variance=variance,
            final_decision=decision,  # type: ignore[arg-type]
            confidence=confidence,
            requires_expert_review=requires_expert_review,
        )


def batch_consensus(
    annotations: list[Annotation],
    variance_threshold: float = 1.0,
    include_threshold: float = 2.0,
    min_annotators: int = 2,
) -> list[ConsensusResult]:
    """Compute consensus for multiple chunk-query pairs in batch.

    Args:
        annotations: List of all annotations
        variance_threshold: Maximum allowed variance (default: 1.0)
        include_threshold: Minimum mean score to include (default: 2.0)
        min_annotators: Minimum annotators required per item (default: 2)

    Returns:
        List of ConsensusResult objects, one per unique (example_id, chunk_id) pair

    Example:
        ```python
        annotations = [...]  # List of Annotation objects
        results = batch_consensus(annotations)
        for result in results:
            if result.final_decision == "include":
                print(f"Include chunk {result.chunk_id}")
        ```

    """
    algorithm = ConsensusAlgorithm(
        variance_threshold=variance_threshold,
        include_threshold=include_threshold,
        min_annotators=min_annotators,
    )

    # Group annotations by (example_id, chunk_id)
    grouped: dict[tuple[str, str], list[Annotation]] = {}
    for ann in annotations:
        key = (ann.example_id, ann.chunk_id)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(ann)

    # Compute consensus for each pair
    results = []
    for (example_id, chunk_id), anns in grouped.items():
        try:
            result = algorithm.compute_consensus(example_id, chunk_id, anns)
            results.append(result)
        except ValueError as e:
            logger.warning(
                "consensus_failed",
                example_id=example_id,
                chunk_id=chunk_id,
                error=str(e),
            )
            continue

    logger.info(
        "batch_consensus_complete",
        total_pairs=len(grouped),
        successful=len(results),
        failed=len(grouped) - len(results),
    )

    return results
