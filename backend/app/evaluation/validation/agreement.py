"""Inter-annotator agreement metrics for human validation.

This module implements Cohen's Kappa and Fleiss' Kappa for measuring
agreement between annotators on chunk-query relevance ratings.

References:
- Landis & Koch (1977) interpretation scale
- Cohen's Kappa: https://en.wikipedia.org/wiki/Cohen%27s_kappa
- Fleiss' Kappa: https://en.wikipedia.org/wiki/Fleiss%27_kappa

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from app.core.logging import get_logger
from app.evaluation.validation.models import AgreementReport, Annotation

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)


def cohens_kappa(ratings_a: list[int], ratings_b: list[int]) -> float:
    """Calculate Cohen's Kappa for two annotators.

    Cohen's Kappa measures inter-rater agreement for categorical ratings,
    accounting for agreement that would occur by chance.

    Args:
        ratings_a: First annotator's ratings (0-3 scale)
        ratings_b: Second annotator's ratings (0-3 scale)

    Returns:
        Cohen's Kappa value (-1 to 1)
        - 1.0 = perfect agreement
        - 0.0 = random agreement
        - negative = systematic disagreement

    Raises:
        ValueError: If rating lists have different lengths

    Example:
        ```python
        ratings_a = [0, 1, 2, 3, 2, 1]
        ratings_b = [0, 1, 2, 3, 1, 1]
        kappa = cohens_kappa(ratings_a, ratings_b)
        print(f"Cohen's Kappa: {kappa:.3f}")
        ```

    """
    if len(ratings_a) != len(ratings_b):
        msg = f"Rating lists must have same length: {len(ratings_a)} vs {len(ratings_b)}"
        raise ValueError(msg)

    if len(ratings_a) == 0:
        return 0.0

    ratings_a_arr = np.array(ratings_a)
    ratings_b_arr = np.array(ratings_b)

    # Observed agreement
    po = np.mean(ratings_a_arr == ratings_b_arr)

    # Expected agreement by chance
    categories = np.unique(np.concatenate([ratings_a_arr, ratings_b_arr]))
    pe = 0.0
    for cat in categories:
        pa = np.mean(ratings_a_arr == cat)
        pb = np.mean(ratings_b_arr == cat)
        pe += pa * pb

    # Cohen's Kappa
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0

    kappa = (po - pe) / (1 - pe)
    return float(kappa)


def fleiss_kappa(ratings_matrix: NDArray[np.int_], categories: list[int] | None = None) -> float:
    """Calculate Fleiss' Kappa for 3+ annotators.

    Fleiss' Kappa generalizes Cohen's Kappa to multiple annotators,
    measuring overall agreement across all raters.

    Args:
        ratings_matrix: Matrix of shape (n_items, n_categories)
            Each row contains counts of how many annotators assigned each category
        categories: List of category values (default: [0, 1, 2, 3])

    Returns:
        Fleiss' Kappa value (0 to 1)
        - 1.0 = perfect agreement
        - 0.0 = random agreement

    Raises:
        ValueError: If ratings_matrix is malformed

    Example:
        ```python
        # 4 items rated by 3 annotators using 4 categories (0-3)
        # Row format: [count_0, count_1, count_2, count_3]
        ratings = np.array(
            [
                [0, 0, 2, 1],  # Item 1: 2 annotators said "2", 1 said "3"
                [0, 1, 2, 0],  # Item 2: 1 annotator said "1", 2 said "2"
                [1, 2, 0, 0],  # Item 3: 1 annotator said "0", 2 said "1"
                [0, 0, 0, 3],  # Item 4: All 3 annotators said "3"
            ]
        )
        kappa = fleiss_kappa(ratings)
        ```

    """
    if categories is None:
        categories = [0, 1, 2, 3]

    n_items, n_categories_actual = ratings_matrix.shape

    if n_items == 0:
        return 0.0

    if n_categories_actual != len(categories):
        msg = (
            f"Categories mismatch: matrix has {n_categories_actual} but {len(categories)} provided"
        )
        raise ValueError(msg)

    # Total annotators per item
    n_annotators = ratings_matrix.sum(axis=1)
    if not np.all(n_annotators > 0):
        msg = "All items must have at least one annotation"
        raise ValueError(msg)

    # Check if all items have same number of annotators
    if not np.all(n_annotators == n_annotators[0]):
        logger.warning(
            "fleiss_kappa_unequal_annotators",
            items=n_items,
            annotators_range=(int(n_annotators.min()), int(n_annotators.max())),
        )

    n = int(n_annotators[0])  # Use first item's count as reference

    # Proportion of assignments to each category (across all items)
    pj = ratings_matrix.sum(axis=0) / (n_items * n)

    # Expected agreement by chance
    pe = float(np.sum(pj**2))

    # Observed agreement for each item
    pi_scores = []
    for i in range(n_items):
        ni = int(n_annotators[i])
        if ni <= 1:
            continue
        nij = ratings_matrix[i, :]
        pi = (np.sum(nij**2) - ni) / (ni * (ni - 1))
        pi_scores.append(pi)

    if not pi_scores:
        return 0.0

    # Mean observed agreement
    po = float(np.mean(pi_scores))

    # Fleiss' Kappa
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0

    kappa = (po - pe) / (1 - pe)
    return float(kappa)


def interpret_kappa(kappa: float) -> str:
    """Interpret kappa value using Landis & Koch (1977) scale.

    Args:
        kappa: Kappa value to interpret

    Returns:
        Human-readable interpretation string

    Example:
        ```python
        kappa = 0.75
        interpretation = interpret_kappa(kappa)
        print(interpretation)  # "substantial"
        ```

    """
    if kappa < 0:
        return "poor"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost_perfect"


@dataclass
class AgreementCalculator:
    """Calculate inter-annotator agreement metrics from annotations.

    This class processes a list of annotations and computes:
    - Cohen's Kappa for 2 annotators
    - Fleiss' Kappa for 3+ annotators
    - Percent agreement
    - Interpretation of agreement strength

    Example:
        ```python
        calculator = AgreementCalculator()
        annotations = [...]  # List of Annotation objects
        report = calculator.calculate(annotations)
        print(f"Agreement: {report.interpretation} (κ={report.cohens_kappa:.3f})")
        ```

    """

    def calculate(self, annotations: list[Annotation]) -> AgreementReport:
        """Calculate agreement metrics from annotations.

        Args:
            annotations: List of annotations to analyze

        Returns:
            AgreementReport with kappa values and interpretation

        Raises:
            ValueError: If fewer than 2 annotators or no annotations

        """
        if not annotations:
            msg = "Cannot calculate agreement: no annotations provided"
            raise ValueError(msg)

        # Group by annotator
        annotator_ratings: dict[str, list[tuple[str, str, int]]] = {}
        for ann in annotations:
            key = (ann.example_id, ann.chunk_id)
            if ann.annotator_id not in annotator_ratings:
                annotator_ratings[ann.annotator_id] = []
            annotator_ratings[ann.annotator_id].append((*key, int(ann.score)))

        n_annotators = len(annotator_ratings)
        if n_annotators < 2:
            msg = f"Need at least 2 annotators, got {n_annotators}"
            raise ValueError(msg)

        # Calculate metrics based on number of annotators
        if n_annotators == 2:
            return self._calculate_cohens(annotator_ratings)
        return self._calculate_fleiss(annotator_ratings)

    def _calculate_cohens(
        self, annotator_ratings: dict[str, list[tuple[str, str, int]]]
    ) -> AgreementReport:
        """Calculate Cohen's Kappa for 2 annotators."""
        annotators = list(annotator_ratings.keys())
        ratings_a_dict = {(ex, ch): score for ex, ch, score in annotator_ratings[annotators[0]]}
        ratings_b_dict = {(ex, ch): score for ex, ch, score in annotator_ratings[annotators[1]]}

        # Find common items
        common_keys = set(ratings_a_dict.keys()) & set(ratings_b_dict.keys())
        if not common_keys:
            msg = "No overlapping items between annotators"
            raise ValueError(msg)

        ratings_a = [ratings_a_dict[k] for k in sorted(common_keys)]
        ratings_b = [ratings_b_dict[k] for k in sorted(common_keys)]

        kappa = cohens_kappa(ratings_a, ratings_b)

        # Calculate percent agreement
        agreements = sum(1 for a, b in zip(ratings_a, ratings_b, strict=True) if a == b)
        percent = agreements / len(ratings_a)

        return AgreementReport(
            cohens_kappa=kappa,
            fleiss_kappa=None,
            percent_agreement=percent,
            interpretation=interpret_kappa(kappa),
        )

    def _calculate_fleiss(
        self, annotator_ratings: dict[str, list[tuple[str, str, int]]]
    ) -> AgreementReport:
        """Calculate Fleiss' Kappa for 3+ annotators."""
        # Build ratings matrix
        all_items: set[tuple[str, str]] = set()
        for ratings in annotator_ratings.values():
            for ex, ch, _score in ratings:
                all_items.add((ex, ch))

        items = sorted(all_items)
        n_categories = 4  # 0-3 scale

        # Build matrix: rows = items, cols = category counts
        matrix = np.zeros((len(items), n_categories), dtype=np.int_)
        for i, item in enumerate(items):
            for ratings in annotator_ratings.values():
                ratings_dict = {(ex, ch): score for ex, ch, score in ratings}
                if item in ratings_dict:
                    score = ratings_dict[item]
                    matrix[i, score] += 1

        kappa = fleiss_kappa(matrix)

        # Calculate percent agreement (exact match among all annotators)
        exact_agreements = 0
        total_items = 0
        for i in range(len(items)):
            if matrix[i].sum() > 1:  # Item has multiple annotations
                # Check if all annotators agreed (one category has all counts)
                if matrix[i].max() == matrix[i].sum():
                    exact_agreements += 1
                total_items += 1

        percent = exact_agreements / total_items if total_items > 0 else 0.0

        return AgreementReport(
            cohens_kappa=None,
            fleiss_kappa=kappa,
            percent_agreement=percent,
            interpretation=interpret_kappa(kappa),
        )
