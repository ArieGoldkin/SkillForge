"""Coarse-to-fine retrieval helper (library-level)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = get_logger(__name__)


def coarse_to_fine(
    coarse_hits: Iterable[dict],
    fine_search_fn,
    *,
    top_k_coarse: int = 5,
    top_k_fine: int = 5,
) -> list[dict]:
    """Retrieve fine results constrained to top coarse sections.

    Args:
        coarse_hits: iterable of coarse results; each must have path metadata.
        fine_search_fn: callable that accepts a list of coarse paths and returns fine hits.
        top_k_coarse: number of coarse sections to consider.
        top_k_fine: number of fine hits to return.

    Returns:
        List of fine hits with path/snippet preserved.

    """
    coarse_list = list(coarse_hits)[:top_k_coarse]
    if not coarse_list:
        return []

    coarse_paths = [hit.get("path") for hit in coarse_list if hit.get("path")]
    fine_hits = fine_search_fn(coarse_paths, top_k=top_k_fine)
    logger.info(
        "coarse_to_fine_complete",
        coarse_considered=len(coarse_list),
        fine_returned=len(fine_hits),
    )
    return list(fine_hits)
