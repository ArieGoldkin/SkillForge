"""Validation manager for orchestrating human validation workflow.

This module provides the main interface for:
- Submitting annotations
- Tracking pending examples
- Computing consensus results
- Generating agreement reports
- Exporting validated datasets
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.core.logging import get_logger
from app.evaluation.validation.agreement import AgreementCalculator
from app.evaluation.validation.consensus import ConsensusAlgorithm
from app.evaluation.validation.models import (
    AgreementReport,
    Annotation,
    ConsensusResult,
)

logger = get_logger(__name__)

ValidationStatus = Literal["pending", "in_progress", "complete", "needs_review"]


@dataclass
class ValidationManager:
    """Orchestrates human validation workflow.

    This class manages the full validation lifecycle:
    1. Submit annotations from multiple annotators
    2. Track which examples are pending review
    3. Compute consensus decisions using 2/3 majority rule
    4. Calculate inter-annotator agreement metrics
    5. Export validated datasets for production use

    Attributes:
        annotations: In-memory storage of all annotations
        consensus_algorithm: Algorithm for computing consensus
        agreement_calculator: Calculator for agreement metrics

    Example:
        ```python
        manager = ValidationManager()

        # Submit annotations
        ann1 = Annotation(
            id="ann-001",
            annotator_id="reviewer1",
            example_id="example-001",
            chunk_id="chunk-042",
            score=RelevanceScore.HIGHLY_RELEVANT,
            confidence=0.9,
        )
        manager.submit_annotation(ann1)

        # Get consensus
        results = manager.get_consensus_results()
        included_chunks = [r.chunk_id for r in results if r.final_decision == "include"]

        # Check agreement
        report = manager.get_agreement_report()
        print(f"Kappa: {report.cohens_kappa:.3f}")

        # Export validated dataset
        manager.export_validated_dataset(Path("validated_dataset.json"))
        ```

    """

    annotations: list[Annotation] = field(default_factory=list)
    consensus_algorithm: ConsensusAlgorithm = field(default_factory=ConsensusAlgorithm)
    agreement_calculator: AgreementCalculator = field(default_factory=AgreementCalculator)

    def submit_annotation(self, annotation: Annotation) -> ValidationStatus:
        """Submit a single annotation.

        Args:
            annotation: Annotation to submit

        Returns:
            Current validation status for the (example_id, chunk_id) pair

        Example:
            ```python
            status = manager.submit_annotation(annotation)
            if status == "complete":
                print("Consensus reached!")
            ```

        """
        self.annotations.append(annotation)

        logger.info(
            "annotation_submitted",
            annotation_id=annotation.id,
            annotator_id=annotation.annotator_id,
            example_id=annotation.example_id,
            chunk_id=annotation.chunk_id,
            score=int(annotation.score),
        )

        # Check if we have enough annotations for consensus
        key = (annotation.example_id, annotation.chunk_id)
        pair_annotations = [a for a in self.annotations if (a.example_id, a.chunk_id) == key]

        n_annotators = len(set(a.annotator_id for a in pair_annotations))

        if n_annotators < self.consensus_algorithm.min_annotators:
            return "pending"

        # Try computing consensus
        try:
            result = self.consensus_algorithm.compute_consensus(
                annotation.example_id, annotation.chunk_id, pair_annotations
            )
            if result.requires_expert_review:
                return "needs_review"
            return "complete"
        except ValueError:
            return "in_progress"

    def get_pending_examples(
        self, annotator_id: str | None = None, limit: int = 10
    ) -> list[dict[str, str]]:
        """Get list of examples pending annotation.

        Args:
            annotator_id: Filter to examples not yet annotated by this annotator
            limit: Maximum number of examples to return

        Returns:
            List of dicts with 'example_id' and 'chunk_id' keys

        Example:
            ```python
            pending = manager.get_pending_examples(annotator_id="reviewer1", limit=5)
            for item in pending:
                print(f"Need annotation for {item['example_id']}/{item['chunk_id']}")
            ```

        """
        # Get all unique (example_id, chunk_id) pairs
        all_pairs = set((ann.example_id, ann.chunk_id) for ann in self.annotations)

        if annotator_id:
            # Filter to pairs not yet annotated by this annotator
            annotated_by_user = set(
                (ann.example_id, ann.chunk_id)
                for ann in self.annotations
                if ann.annotator_id == annotator_id
            )
            pending_pairs = all_pairs - annotated_by_user
        else:
            # Filter to pairs with < min_annotators unique annotators
            pending_pairs = set()
            for pair in all_pairs:
                pair_annotations = [
                    a for a in self.annotations if (a.example_id, a.chunk_id) == pair
                ]
                n_annotators = len(set(a.annotator_id for a in pair_annotations))
                if n_annotators < self.consensus_algorithm.min_annotators:
                    pending_pairs.add(pair)

        # Convert to list and limit
        result = [{"example_id": ex, "chunk_id": ch} for ex, ch in sorted(pending_pairs)[:limit]]

        logger.debug(
            "pending_examples_retrieved",
            annotator_id=annotator_id,
            count=len(result),
            total_pending=len(pending_pairs),
        )

        return result

    def get_consensus_results(self) -> list[ConsensusResult]:
        """Get consensus results for all annotated pairs.

        Returns:
            List of ConsensusResult objects

        Example:
            ```python
            results = manager.get_consensus_results()
            for result in results:
                print(f"{result.chunk_id}: {result.final_decision}")
            ```

        """
        # Group annotations by (example_id, chunk_id)
        grouped: dict[tuple[str, str], list[Annotation]] = {}
        for ann in self.annotations:
            key = (ann.example_id, ann.chunk_id)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(ann)

        # Compute consensus for pairs with enough annotators
        results = []
        for (example_id, chunk_id), anns in grouped.items():
            n_annotators = len(set(a.annotator_id for a in anns))
            if n_annotators >= self.consensus_algorithm.min_annotators:
                try:
                    result = self.consensus_algorithm.compute_consensus(example_id, chunk_id, anns)
                    results.append(result)
                except ValueError as e:
                    logger.warning(
                        "consensus_computation_failed",
                        example_id=example_id,
                        chunk_id=chunk_id,
                        error=str(e),
                    )

        logger.info(
            "consensus_results_retrieved",
            total_results=len(results),
            included=sum(1 for r in results if r.final_decision == "include"),
            excluded=sum(1 for r in results if r.final_decision == "exclude"),
            needs_review=sum(1 for r in results if r.final_decision == "review"),
        )

        return results

    def get_agreement_report(self) -> AgreementReport:
        """Generate inter-annotator agreement report.

        Returns:
            AgreementReport with kappa values and interpretation

        Raises:
            ValueError: If fewer than 2 annotators or no annotations

        Example:
            ```python
            report = manager.get_agreement_report()
            print(f"Agreement: {report.interpretation}")
            print(f"Kappa: {report.cohens_kappa or report.fleiss_kappa:.3f}")
            ```

        """
        if not self.annotations:
            msg = "Cannot generate agreement report: no annotations"
            raise ValueError(msg)

        report = self.agreement_calculator.calculate(self.annotations)

        logger.info(
            "agreement_report_generated",
            cohens_kappa=report.cohens_kappa,
            fleiss_kappa=report.fleiss_kappa,
            percent_agreement=report.percent_agreement,
            interpretation=report.interpretation,
        )

        return report

    def export_validated_dataset(self, output_path: Path, include_drafts: bool = False) -> int:
        """Export validated dataset with consensus decisions.

        Creates a JSON file containing:
        - Original examples
        - Consensus decisions (include/exclude/review)
        - Agreement metrics
        - Annotation metadata

        Args:
            output_path: Path to save dataset JSON
            include_drafts: If True, include items pending full validation

        Returns:
            Number of examples exported

        Example:
            ```python
            count = manager.export_validated_dataset(
                Path("validated_dataset.json"), include_drafts=False
            )
            print(f"Exported {count} validated examples")
            ```

        """
        results = self.get_consensus_results()

        # Filter based on include_drafts
        if not include_drafts:
            results = [r for r in results if r.final_decision in ["include", "exclude"]]

        # Build export data
        export_data = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": "human_validated_dataset",
                "task_type": "validation",
                "created_at": datetime.now(UTC).isoformat(),
                "description": "Human-validated chunk-query relevance dataset",
                "n_annotators": len(set(a.annotator_id for a in self.annotations)),
                "total_annotations": len(self.annotations),
            },
            "examples": [],
        }

        # Add consensus results as examples
        for result in results:
            example = {
                "example_id": result.example_id,
                "chunk_id": result.chunk_id,
                "consensus": {
                    "decision": result.final_decision,
                    "mean_score": result.mean_score,
                    "variance": result.variance,
                    "confidence": result.confidence,
                    "requires_expert_review": result.requires_expert_review,
                },
                "annotations": [
                    {
                        "annotator_id": ann.annotator_id,
                        "score": int(ann.score),
                        "confidence": ann.confidence,
                        "timestamp": ann.timestamp.isoformat(),
                    }
                    for ann in result.annotations
                ],
            }
            export_data["examples"].append(example)

        # Add agreement report if possible
        try:
            report = self.get_agreement_report()
            export_data["agreement_metrics"] = {
                "cohens_kappa": report.cohens_kappa,
                "fleiss_kappa": report.fleiss_kappa,
                "percent_agreement": report.percent_agreement,
                "interpretation": report.interpretation,
            }
        except ValueError:
            logger.warning("agreement_report_unavailable", reason="insufficient_data")

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(
            "validated_dataset_exported",
            path=str(output_path),
            example_count=len(results),
            include_drafts=include_drafts,
        )

        return len(results)
