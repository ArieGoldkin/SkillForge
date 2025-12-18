"""Structural prior scoring based on chunk metadata.

This module provides scoring functions that leverage chunk metadata
to boost results based on structural relevance signals:

- Section/title presence: Chunks with explicit sections are more likely to be topical
- Path depth: Shallower paths often indicate more fundamental/overview content
- Position in section: Early chunks often contain definitions/summaries
- Content type: Different types have different relevance patterns

These priors are combined with LLM scores to improve ranking quality.
"""

from dataclasses import dataclass

from app.core.constants import (
    STRUCTURAL_PATH_DEPTH_THRESHOLD,
    STRUCTURAL_POSITION_EARLY_THRESHOLD,
    STRUCTURAL_POSITION_LATE_THRESHOLD,
    STRUCTURAL_WEIGHT_CODE_BLOCK,
    STRUCTURAL_WEIGHT_HEADING,
    STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY,
    STRUCTURAL_WEIGHT_POSITION_EARLY,
    STRUCTURAL_WEIGHT_POSITION_LATE,
    STRUCTURAL_WEIGHT_SECTION_PRESENT,
)
from app.schemas.search import ChunkMetadata


@dataclass
class StructuralWeights:
    """Weights for structural prior components.

    Attributes:
        section_present: Boost for having explicit section title
        path_depth_penalty: Penalty per extra path level beyond 2
        position_early: Boost for chunks in first 20% of section
        position_late: Penalty for chunks in last 20% of section
        code_block: Boost for code block chunks
        heading: Boost for heading chunks

    """

    section_present: float = STRUCTURAL_WEIGHT_SECTION_PRESENT
    path_depth_penalty: float = STRUCTURAL_WEIGHT_PATH_DEPTH_PENALTY
    position_early: float = STRUCTURAL_WEIGHT_POSITION_EARLY
    position_late: float = STRUCTURAL_WEIGHT_POSITION_LATE
    code_block: float = STRUCTURAL_WEIGHT_CODE_BLOCK
    heading: float = STRUCTURAL_WEIGHT_HEADING


class StructuralPriorScorer:
    """Calculator for structural prior scores.

    Uses chunk metadata to compute relevance priors that complement
    semantic/LLM scoring. Scores are additive boosts/penalties that
    modify the base score.

    Example:
        >>> scorer = StructuralPriorScorer()
        >>> metadata = ChunkMetadata(section="Introduction", chunk_idx=0, chunk_total=10)
        >>> score = scorer.score_single(metadata)
        >>> print(f"Structural prior: {score}")
        Structural prior: 0.2

    """

    def __init__(self, weights: StructuralWeights | None = None) -> None:
        """Initialize with optional custom weights.

        Args:
            weights: Custom weights for scoring. If None, uses defaults from constants.

        """
        self.weights = weights or StructuralWeights()

    def score_batch(
        self,
        metadata_list: list[ChunkMetadata],
    ) -> list[float]:
        """Score multiple chunks for structural priors.

        Args:
            metadata_list: List of ChunkMetadata to score

        Returns:
            List of structural prior scores (typically -0.2 to +0.3)

        """
        return [self.score_single(metadata) for metadata in metadata_list]

    def score_single(self, metadata: ChunkMetadata) -> float:
        """Calculate structural prior for single chunk.

        The structural prior is a sum of boosts/penalties based on:
        1. Section presence: +0.10 if section title exists
        2. Path depth: -0.05 per level beyond depth 2
        3. Position: +0.10 for first 20%, -0.05 for last 20%
        4. Chunk type: +0.05 for code, +0.10 for headings

        Args:
            metadata: Chunk metadata containing structural information

        Returns:
            Structural prior score (typically -0.2 to +0.3)

        """
        score = 0.0

        # Section presence boost
        if metadata.section:
            score += self.weights.section_present

        # Path depth penalty (deeper = less fundamental)
        if metadata.path:
            path_list = metadata.path if isinstance(metadata.path, list) else []
            depth = len(path_list)
            if depth > STRUCTURAL_PATH_DEPTH_THRESHOLD:
                score -= self.weights.path_depth_penalty * (depth - STRUCTURAL_PATH_DEPTH_THRESHOLD)

        # Position-based scoring
        if metadata.chunk_idx is not None and metadata.chunk_total is not None:
            chunk_total = max(metadata.chunk_total, 1)  # Avoid division by zero
            position_ratio = metadata.chunk_idx / chunk_total

            if position_ratio < STRUCTURAL_POSITION_EARLY_THRESHOLD:
                score += self.weights.position_early
            elif position_ratio > STRUCTURAL_POSITION_LATE_THRESHOLD:
                score += self.weights.position_late  # This is already negative

        # Chunk type bonuses
        chunk_type = metadata.chunk_type or ""
        if chunk_type == "code_block":
            score += self.weights.code_block
        elif chunk_type == "heading":
            score += self.weights.heading

        return score
