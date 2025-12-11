"""Human validation workflow for golden datasets.

This module provides tools for collecting human annotations on chunk-query relevance
and computing inter-annotator agreement metrics:
- Multi-annotator relevance scoring (0-3 scale)
- Cohen's Kappa and Fleiss' Kappa for agreement
- 2/3 majority rule consensus algorithm
- Export validated datasets for production use

Usage:
    ```python
    from app.evaluation.validation import ValidationManager, RelevanceScore

    # Submit annotations
    manager = ValidationManager()
    annotation = Annotation(
        id="ann-001",
        annotator_id="reviewer1",
        example_id="example-001",
        chunk_id="chunk-042",
        score=RelevanceScore.HIGHLY_RELEVANT,
        confidence=0.9,
    )
    manager.submit_annotation(annotation)

    # Check consensus
    results = manager.get_consensus_results()
    for result in results:
        if result.final_decision == "include":
            print(f"Chunk {result.chunk_id} approved")

    # Check agreement
    report = manager.get_agreement_report()
    print(f"Cohen's Kappa: {report.cohens_kappa:.3f}")
    ```
"""

from app.evaluation.validation.agreement import (
    AgreementCalculator,
    cohens_kappa,
    fleiss_kappa,
    interpret_kappa,
)
from app.evaluation.validation.consensus import (
    ConsensusAlgorithm,
    batch_consensus,
)
from app.evaluation.validation.manager import (
    ValidationManager,
    ValidationStatus,
)
from app.evaluation.validation.models import (
    AgreementReport,
    Annotation,
    ConsensusResult,
    RelevanceScore,
)

__all__ = [
    # Models
    "RelevanceScore",
    "Annotation",
    "ConsensusResult",
    "AgreementReport",
    "ValidationStatus",
    # Agreement
    "cohens_kappa",
    "fleiss_kappa",
    "interpret_kappa",
    "AgreementCalculator",
    # Consensus
    "ConsensusAlgorithm",
    "batch_consensus",
    # Manager
    "ValidationManager",
]
