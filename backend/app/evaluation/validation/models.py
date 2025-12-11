"""Data models for human validation workflow.

This module defines the core data structures for the human validation process:
- RelevanceScore: 0-3 scale for chunk-query relevance
- Annotation: Single annotator's rating
- ConsensusResult: Aggregated decision from multiple annotators
- AgreementReport: Inter-annotator agreement metrics
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field


class RelevanceScore(IntEnum):
    """Relevance score for chunk-query pairs (0-3 scale).

    0 = IRRELEVANT: Chunk is completely unrelated to query
    1 = TANGENTIAL: Chunk mentions related concepts but doesn't address query
    2 = PARTIAL: Chunk partially addresses query, missing key aspects
    3 = HIGHLY_RELEVANT: Chunk directly and comprehensively addresses query
    """

    IRRELEVANT = 0
    TANGENTIAL = 1
    PARTIAL = 2
    HIGHLY_RELEVANT = 3


class Annotation(BaseModel):
    """Single annotator's relevance rating for a chunk-query pair.

    Attributes:
        id: Unique annotation identifier
        annotator_id: ID of the annotator who provided this rating
        example_id: ID of the evaluation example (query)
        chunk_id: ID of the chunk being rated
        score: Relevance score (0-3)
        confidence: Annotator's confidence in their rating (0.0-1.0)
        notes: Optional notes explaining the rating
        timestamp: When this annotation was created

    """

    id: str
    annotator_id: str
    example_id: str
    chunk_id: str
    score: RelevanceScore
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConsensusResult(BaseModel):
    """Consensus decision from multiple annotators on a chunk-query pair.

    Attributes:
        example_id: ID of the evaluation example (query)
        chunk_id: ID of the chunk being evaluated
        annotations: List of annotations used to compute consensus
        mean_score: Average relevance score across annotators
        variance: Score variance across annotators
        final_decision: Include/exclude/review decision
        confidence: Confidence in the consensus (0.0-1.0)
        requires_expert_review: Whether expert review is needed

    """

    example_id: str
    chunk_id: str
    annotations: list[Annotation]
    mean_score: float
    variance: float
    final_decision: Literal["include", "exclude", "review"]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_expert_review: bool


class AgreementReport(BaseModel):
    """Inter-annotator agreement report.

    Attributes:
        cohens_kappa: Cohen's Kappa for 2 annotators (if applicable)
        fleiss_kappa: Fleiss' Kappa for 3+ annotators (if applicable)
        percent_agreement: Raw percentage agreement
        interpretation: Human-readable interpretation of kappa values

    """

    cohens_kappa: float | None = None
    fleiss_kappa: float | None = None
    percent_agreement: float = Field(ge=0.0, le=1.0)
    interpretation: str
