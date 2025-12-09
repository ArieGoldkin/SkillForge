"""Reciprocal Rank Fusion (RRF) for hybrid search result merging.

This module implements the RRF algorithm for combining ranked results
from multiple search strategies (semantic and keyword search).

The RRF algorithm provides a robust method for combining rankings without
requiring score normalization, making it ideal for hybrid search where
different retrieval methods produce incomparable scores.

References:
    Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
    "Reciprocal rank fusion outperforms condorcet and individual rank learning methods."
    SIGIR 2009.

"""

from collections import defaultdict


def reciprocal_rank_fusion[T](
    result_lists: list[list[tuple[T, float]]],
    k: int = 60,
) -> list[tuple[T, float]]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion.

    RRF computes a combined score for each item based on its rank position
    across all input lists. The formula is:

        RRF_score(item) = Σ 1 / (k + rank(item))

    where the sum is over all rankers, and rank starts at 1 for the top item.

    The constant k (typically 60) prevents items ranked first from dominating
    and provides smoothing for the reciprocal function.

    Args:
        result_lists: List of ranked result lists. Each inner list contains
            (item, score) tuples sorted by relevance. The score values are
            not used in RRF calculation - only the rank positions matter.
        k: RRF constant for smoothing (default: 60, standard value from literature)

    Returns:
        List of (item, rrf_score) tuples sorted by RRF score in descending order.
        Higher RRF scores indicate better overall ranking across all input lists.

    Example:
        >>> semantic_results = [("doc1", 0.95), ("doc2", 0.80), ("doc3", 0.75)]
        >>> keyword_results = [("doc2", 10.5), ("doc1", 8.2), ("doc4", 7.1)]
        >>> fused = reciprocal_rank_fusion([semantic_results, keyword_results])
        >>> fused[0][0]  # Best result after fusion
        'doc2'

    Note:
        - Items must be hashable (typically strings or UUIDs)
        - Input lists should be sorted by relevance (best first)
        - Items appearing in multiple lists receive higher combined scores

    """
    # Accumulate RRF scores for each unique item
    rrf_scores: dict[T, float] = defaultdict(float)

    # Process each ranked list
    for result_list in result_lists:
        # Iterate through results with their rank positions (1-indexed)
        for rank, (item, _original_score) in enumerate(result_list, start=1):
            # Add reciprocal rank contribution to item's total score
            rrf_scores[item] += 1.0 / (k + rank)

    # Convert to list of tuples and sort by RRF score (descending)
    fused_results = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return fused_results
