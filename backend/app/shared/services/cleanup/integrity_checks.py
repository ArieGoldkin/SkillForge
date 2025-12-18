"""Vector integrity checks for embeddings.

Detects corrupted vectors:
- Length mismatch (expected 1536 dimensions)
- NULL vectors that shouldn't be NULL
- Invalid vector values (NaN, Inf)
"""

import uuid
from datetime import UTC, datetime
from math import inf, isfinite, isnan

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.analysis_chunk import AnalysisChunk

logger = get_logger(__name__)

# Expected vector dimensions for OpenAI text-embedding-3-small
EXPECTED_DIMENSIONS = 1536

# Maximum number of issues to show in report summaries
MAX_REPORT_EXAMPLES = 10


class VectorIntegrityChecker:
    """Service for detecting vector integrity issues.

    Checks for:
    1. Vector dimension mismatches
    2. NULL vectors in required fields
    3. Invalid values (NaN, Inf)
    4. Zero vectors (all zeros)
    5. Non-normalized vectors (for cosine similarity)
    """

    def __init__(
        self,
        session: AsyncSession,
        batch_size: int = 1000,
    ) -> None:
        """Initialize integrity checker.

        Args:
            session: Async database session
            batch_size: Number of records to check per batch

        """
        self.session = session
        self.batch_size = batch_size

    async def check_chunk_vector_dimensions(self) -> list[uuid.UUID]:
        """Find chunks with incorrect vector dimensions.

        Expected: 1536 dimensions (OpenAI text-embedding-3-small)
        This should not happen in normal operation, but can occur with:
        - Manual database edits
        - Migration errors
        - Embedding model changes

        Returns:
            List of chunk IDs with dimension mismatches

        Example:
            >>> checker = VectorIntegrityChecker(session)
            >>> invalid_ids = await checker.check_chunk_vector_dimensions()
            >>> print(f"Found {len(invalid_ids)} chunks with invalid dimensions")

        """
        # pgvector provides vector_dims() function to get vector dimensionality
        # Check if dimension != EXPECTED_DIMENSIONS
        query = select(AnalysisChunk.id).where(
            func.vector_dims(AnalysisChunk.vector) != EXPECTED_DIMENSIONS
        )

        result = await self.session.execute(query)
        invalid_ids = [row[0] for row in result.all()]

        logger.info(
            "check_chunk_vector_dimensions",
            invalid_count=len(invalid_ids),
            expected_dimensions=EXPECTED_DIMENSIONS,
        )

        return invalid_ids

    async def check_analysis_vector_dimensions(self) -> list[uuid.UUID]:
        """Find analyses with incorrect embedding dimensions.

        Similar to chunk check, but for analysis-level embeddings.

        Returns:
            List of analysis IDs with dimension mismatches

        Example:
            >>> invalid_ids = await checker.check_analysis_vector_dimensions()

        """
        query = select(Analysis.id).where(
            Analysis.content_embedding.isnot(None),
            func.vector_dims(Analysis.content_embedding) != EXPECTED_DIMENSIONS,
        )

        result = await self.session.execute(query)
        invalid_ids = [row[0] for row in result.all()]

        logger.info(
            "check_analysis_vector_dimensions",
            invalid_count=len(invalid_ids),
            expected_dimensions=EXPECTED_DIMENSIONS,
        )

        return invalid_ids

    async def check_null_chunk_vectors(self) -> list[uuid.UUID]:
        """Find chunks with NULL vectors (should always have embeddings).

        Chunks with NULL vectors indicate:
        - Embedding generation failure
        - Incomplete workflow execution
        - Data corruption

        Returns:
            List of chunk IDs with NULL vectors

        Example:
            >>> null_ids = await checker.check_null_chunk_vectors()
            >>> print(f"Found {len(null_ids)} chunks with NULL vectors")

        """
        query = select(AnalysisChunk.id).where(AnalysisChunk.vector.is_(None))

        result = await self.session.execute(query)
        null_ids = [row[0] for row in result.all()]

        logger.warning(
            "check_null_chunk_vectors",
            null_count=len(null_ids),
        )

        return null_ids

    async def check_null_analysis_embeddings(
        self,
        only_completed: bool = True,
    ) -> list[uuid.UUID]:
        """Find completed analyses with NULL embeddings.

        Args:
            only_completed: Only check analyses with status='complete'

        Returns:
            List of analysis IDs with NULL embeddings

        Example:
            >>> null_ids = await checker.check_null_analysis_embeddings()

        """
        query = select(Analysis.id).where(Analysis.content_embedding.is_(None))

        if only_completed:
            query = query.where(Analysis.status == "complete")

        result = await self.session.execute(query)
        null_ids = [row[0] for row in result.all()]

        logger.warning(
            "check_null_analysis_embeddings",
            null_count=len(null_ids),
            only_completed=only_completed,
        )

        return null_ids

    async def check_invalid_values_in_chunks(
        self,
        check_batch_size: int = 100,
    ) -> list[tuple[uuid.UUID, str]]:
        """Find chunks with invalid values (NaN, Inf) in vectors.

        This requires fetching vectors from database and checking values
        in application code, as pgvector doesn't have built-in NaN/Inf checks.

        Args:
            check_batch_size: Number of chunks to check per batch

        Returns:
            List of tuples (chunk_id, issue_description)

        Example:
            >>> issues = await checker.check_invalid_values_in_chunks()
            >>> for chunk_id, issue in issues:
            ...     print(f"Chunk {chunk_id}: {issue}")

        """
        issues: list[tuple[uuid.UUID, str]] = []

        # Stream all chunks in batches
        offset = 0
        while True:
            query = (
                select(AnalysisChunk.id, AnalysisChunk.vector)
                .where(AnalysisChunk.vector.isnot(None))
                .limit(check_batch_size)
                .offset(offset)
            )

            result = await self.session.execute(query)
            rows = result.all()

            if not rows:
                break

            for chunk_id, vector in rows:
                if vector is None:
                    continue

                # Check for NaN values
                nan_count = sum(1 for v in vector if isnan(v))
                if nan_count > 0:
                    issues.append((chunk_id, f"Contains {nan_count} NaN values"))

                # Check for Inf values
                inf_count = sum(1 for v in vector if v in {inf, -inf})
                if inf_count > 0:
                    issues.append((chunk_id, f"Contains {inf_count} Inf values"))

                # Check for all finite values
                if not all(isfinite(v) for v in vector):
                    issues.append((chunk_id, "Contains non-finite values"))

            offset += check_batch_size

            logger.info(
                "check_invalid_values_progress",
                checked=offset,
                issues_found=len(issues),
            )

        logger.info(
            "check_invalid_values_in_chunks_complete",
            total_issues=len(issues),
        )

        return issues

    async def check_zero_vectors_in_chunks(self) -> list[uuid.UUID]:
        """Find chunks with zero vectors (all zeros).

        Zero vectors indicate:
        - Embedding model failure
        - Data corruption
        - Incorrect initialization

        Returns:
            List of chunk IDs with zero vectors

        Example:
            >>> zero_ids = await checker.check_zero_vectors_in_chunks()

        """
        zero_vector_ids: list[uuid.UUID] = []

        # Stream chunks in batches
        offset = 0
        while True:
            query = (
                select(AnalysisChunk.id, AnalysisChunk.vector)
                .where(AnalysisChunk.vector.isnot(None))
                .limit(self.batch_size)
                .offset(offset)
            )

            result = await self.session.execute(query)
            rows = result.all()

            if not rows:
                break

            for chunk_id, vector in rows:
                if vector is None:
                    continue

                # Check if all values are zero
                if all(v == 0.0 for v in vector):
                    zero_vector_ids.append(chunk_id)

            offset += self.batch_size

            logger.info(
                "check_zero_vectors_progress",
                checked=offset,
                zero_vectors_found=len(zero_vector_ids),
            )

        logger.info(
            "check_zero_vectors_in_chunks_complete",
            zero_vector_count=len(zero_vector_ids),
        )

        return zero_vector_ids

    async def check_vector_normalization(
        self,
        tolerance: float = 1e-5,
    ) -> list[tuple[uuid.UUID, float]]:
        """Find chunks with non-normalized vectors (L2 norm != 1.0).

        For cosine similarity, vectors should be normalized.
        OpenAI embeddings are pre-normalized, but manual edits may break this.

        Args:
            tolerance: Acceptable deviation from unit norm (default: 1e-5)

        Returns:
            List of tuples (chunk_id, actual_norm)

        Example:
            >>> issues = await checker.check_vector_normalization()
            >>> for chunk_id, norm in issues:
            ...     print(f"Chunk {chunk_id} has norm {norm} (expected ~1.0)")

        """
        non_normalized: list[tuple[uuid.UUID, float]] = []

        # Stream chunks in batches
        offset = 0
        while True:
            query = (
                select(AnalysisChunk.id, AnalysisChunk.vector)
                .where(AnalysisChunk.vector.isnot(None))
                .limit(self.batch_size)
                .offset(offset)
            )

            result = await self.session.execute(query)
            rows = result.all()

            if not rows:
                break

            for chunk_id, vector in rows:
                if vector is None:
                    continue

                # Calculate L2 norm
                norm = sum(v * v for v in vector) ** 0.5

                # Check if norm is approximately 1.0
                if abs(norm - 1.0) > tolerance:
                    non_normalized.append((chunk_id, norm))

            offset += self.batch_size

            logger.info(
                "check_vector_normalization_progress",
                checked=offset,
                non_normalized_found=len(non_normalized),
            )

        logger.info(
            "check_vector_normalization_complete",
            non_normalized_count=len(non_normalized),
            tolerance=tolerance,
        )

        return non_normalized

    async def run_all_checks(self) -> dict[str, list]:
        """Run all integrity checks and return comprehensive report.

        Returns:
            Dictionary with all integrity check results

        Example:
            >>> checker = VectorIntegrityChecker(session)
            >>> report = await checker.run_all_checks()
            >>> print(f"Found {len(report['chunk_dimension_issues'])} dimension issues")

        """
        report: dict[str, list] = {
            "chunk_dimension_issues": [],
            "analysis_dimension_issues": [],
            "null_chunk_vectors": [],
            "null_analysis_embeddings": [],
            "invalid_values": [],
            "zero_vectors": [],
            "non_normalized_vectors": [],
        }

        logger.info("run_all_checks_started")

        # 1. Check dimensions
        report["chunk_dimension_issues"] = await self.check_chunk_vector_dimensions()
        report["analysis_dimension_issues"] = await self.check_analysis_vector_dimensions()

        # 2. Check NULL vectors
        report["null_chunk_vectors"] = await self.check_null_chunk_vectors()
        report["null_analysis_embeddings"] = await self.check_null_analysis_embeddings()

        # 3. Check invalid values (NaN, Inf)
        report["invalid_values"] = await self.check_invalid_values_in_chunks()

        # 4. Check zero vectors
        report["zero_vectors"] = await self.check_zero_vectors_in_chunks()

        # 5. Check normalization
        report["non_normalized_vectors"] = await self.check_vector_normalization()

        # Calculate summary statistics
        total_issues = sum(len(v) if isinstance(v, list) else 0 for v in report.values())

        logger.info(
            "run_all_checks_complete",
            total_issues=total_issues,
            chunk_dimension_issues=len(report["chunk_dimension_issues"]),
            analysis_dimension_issues=len(report["analysis_dimension_issues"]),
            null_chunk_vectors=len(report["null_chunk_vectors"]),
            null_analysis_embeddings=len(report["null_analysis_embeddings"]),
            invalid_values=len(report["invalid_values"]),
            zero_vectors=len(report["zero_vectors"]),
            non_normalized_vectors=len(report["non_normalized_vectors"]),
        )

        return report

    async def generate_integrity_report_markdown(self) -> str:
        """Generate human-readable integrity report in Markdown format.

        Returns:
            Markdown-formatted report string

        Example:
            >>> report = await checker.generate_integrity_report_markdown()
            >>> print(report)

        """
        report = await self.run_all_checks()

        lines = [
            "# Vector Integrity Report",
            "",
            f"Generated at: {datetime.now(UTC).isoformat()}",
            "",
            "## Summary",
            "",
        ]

        # Add summary statistics
        for check_name, results in report.items():
            count = len(results) if isinstance(results, list) else 0
            status = "✅ PASS" if count == 0 else "❌ FAIL"
            lines.append(f"- **{check_name}**: {status} ({count} issues)")

        # Add detailed sections
        for check_name, results in report.items():
            if not results:
                continue

            lines.extend(
                [
                    "",
                    f"## {check_name.replace('_', ' ').title()}",
                    "",
                    f"Found {len(results)} issues:",
                    "",
                ]
            )

            # Add first issues as examples (limit to MAX_REPORT_EXAMPLES)
            for i, result in enumerate(results[:MAX_REPORT_EXAMPLES], 1):
                if isinstance(result, tuple):
                    lines.append(f"{i}. {result}")
                else:
                    lines.append(f"{i}. {result}")

            if len(results) > MAX_REPORT_EXAMPLES:
                lines.append(f"... and {len(results) - MAX_REPORT_EXAMPLES} more")

        return "\n".join(lines)
