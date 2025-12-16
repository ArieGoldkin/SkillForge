# Issue #220: Architecture Design - PII/Safety Guardrails

**Version:** 1.0
**Date:** December 10, 2025

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [PII Detection Service](#2-pii-detection-service)
3. [Pipeline Integration](#3-pipeline-integration)
4. [Cleanup Services](#4-cleanup-services)
5. [Database Schema](#5-database-schema)
6. [Configuration](#6-configuration)
7. [API Contracts](#7-api-contracts)
8. [Testing Strategy](#8-testing-strategy)

---

## 1. System Overview

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EMBEDDING PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────┐     ┌───────────────┐     ┌──────────────┐     ┌──────────┐ │
│  │  Extract  │────▶│  PII Screener │────▶│   Chunker    │────▶│ Embedder │ │
│  │  Content  │     │  (NEW #220)   │     │              │     │          │ │
│  └───────────┘     └───────────────┘     └──────────────┘     └──────────┘ │
│                           │                                         │       │
│                           ▼                                         ▼       │
│                    ┌──────────────┐                         ┌──────────────┐│
│                    │  PIIResult   │                         │AnalysisChunk ││
│                    │  (metadata)  │                         │ (+ pii_flag) ││
│                    └──────────────┘                         └──────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLEANUP & INTEGRITY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐   ┌───────────────────┐   ┌────────────────┐            │
│  │ OrphanCleaner │   │ IntegrityChecker  │   │   TTLManager   │            │
│  │               │   │                   │   │                │            │
│  │ - Detect      │   │ - Dimension check │   │ - Draft expiry │            │
│  │ - Batch del   │   │ - NaN/Inf check   │   │ - Cascade del  │            │
│  │ - FK cascade  │   │ - Zero vector     │   │                │            │
│  └───────────────┘   └───────────────────┘   └────────────────┘            │
│         │                     │                      │                      │
│         └─────────────────────┴──────────────────────┘                      │
│                               │                                             │
│                               ▼                                             │
│                      ┌────────────────┐                                     │
│                      │ CleanupService │  Scheduled daily / on-demand        │
│                      │   (facade)     │                                     │
│                      └────────────────┘                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
                    ┌─────────────────────────────────────────┐
                    │           RAW CONTENT (str)             │
                    └─────────────────────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │          PII DETECTION                  │
                    │  ┌─────────────────────────────────┐    │
                    │  │  Regex Scan (email, phone, etc) │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  Optional: Presidio NER Scan    │    │
                    │  └─────────────────────────────────┘    │
                    └─────────────────────────────────────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                    ┌───────────────┐       ┌───────────────┐
                    │  pii_flag=F   │       │  pii_flag=T   │
                    │  Continue     │       │  Check action │
                    └───────────────┘       └───────────────┘
                            │                       │
                            │               ┌───────┴───────┐
                            │               ▼               ▼
                            │       ┌───────────┐   ┌───────────┐
                            │       │action=flag│   │action=rej │
                            │       │ Continue  │   │   STOP    │
                            │       └───────────┘   └───────────┘
                            │               │
                            └───────┬───────┘
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │           CHUNKING (existing)           │
                    │  - Coarse chunks (paragraphs)           │
                    │  - Fine chunks (windowed)               │
                    │  - Summaries (optional)                 │
                    └─────────────────────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │          EMBEDDING (existing)           │
                    │  - OpenAI text-embedding-3-small        │
                    │  - L2 normalization                     │
                    └─────────────────────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │            STORAGE                      │
                    │  - analysis_chunks table                │
                    │  - pii_flag + pii_types columns (NEW)   │
                    │  - vector (pgvector 1536-dim)           │
                    └─────────────────────────────────────────┘
```

---

## 2. PII Detection Service

### 2.1 Class Hierarchy

```
services/pii/
├── __init__.py          # Exports: PIIDetector, PIIResult, PIIType
├── types.py             # Enums and dataclasses
├── patterns.py          # Regex pattern definitions
└── detector.py          # Main PIIDetector class
```

### 2.2 Type Definitions (types.py)

```python
from dataclasses import dataclass, field
from enum import Enum


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE_US = "phone_us"
    PHONE_INTL = "phone_intl"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    STRIPE_KEY = "stripe_key"
    NAME = "name"  # Presidio only
    ORGANIZATION = "organization"  # Presidio only


class SensitivityLevel(str, Enum):
    """Sensitivity levels for PII detection."""

    LOW = "low"  # email only
    MEDIUM = "medium"  # email, phone, SSN, credit card
    HIGH = "high"  # all regex + API keys
    MAXIMUM = "maximum"  # all + Presidio NER


class PIIAction(str, Enum):
    """Action to take when PII is detected."""

    FLAG = "flag"  # Continue with flag in metadata
    REJECT = "reject"  # Fail the workflow


@dataclass
class PIIMatch:
    """A single PII match (without the actual value)."""

    pii_type: PIIType
    start: int  # Character offset (for debugging, not value)
    end: int
    # Note: NO value field - we never store the actual PII


@dataclass
class PIIResult:
    """Result of PII detection scan."""

    has_pii: bool
    types: list[PIIType] = field(default_factory=list)
    match_count: int = 0
    matches_by_type: dict[PIIType, int] = field(default_factory=dict)

    @property
    def should_reject(self) -> bool:
        """Check if content should be rejected based on config."""
        from app.core.config import settings

        if not self.has_pii:
            return False
        if settings.PII_ACTION == PIIAction.REJECT:
            return True
        return False

    def to_metadata(self) -> dict:
        """Convert to metadata dict for storage (no raw values)."""
        return {
            "pii_flag": self.has_pii,
            "pii_types": [t.value for t in self.types],
            "pii_count": self.match_count,
        }
```

### 2.3 Regex Patterns (patterns.py)

```python
"""PII detection regex patterns.

These patterns are designed for high recall (catch most PII)
with reasonable precision. False positives are acceptable
since we only flag, not redact.
"""

import re
from typing import Final

# Pre-compiled patterns for performance
PII_PATTERNS: Final[dict[str, re.Pattern]] = {
    # Email: RFC 5322 simplified
    "email": re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    ),

    # US Phone: (555) 123-4567, 555-123-4567, +1 555 123 4567
    "phone_us": re.compile(
        r"\b(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),

    # International Phone: +44 20 7123 4567, +49 30 12345678
    "phone_intl": re.compile(
        r"\+(?:[0-9][-.\s]?){6,14}[0-9]"
    ),

    # SSN: 123-45-6789, 123 45 6789
    "ssn": re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    ),

    # Credit Card: Visa, Mastercard, Amex, Discover
    "credit_card": re.compile(
        r"\b(?:"
        r"4[0-9]{12}(?:[0-9]{3})?"  # Visa
        r"|5[1-5][0-9]{14}"  # Mastercard
        r"|3[47][0-9]{13}"  # Amex
        r"|6(?:011|5[0-9]{2})[0-9]{12}"  # Discover
        r")\b"
    ),

    # IPv4: 192.168.1.1
    "ipv4": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ),

    # IPv6: Simplified pattern
    "ipv6": re.compile(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    ),

    # AWS Access Key ID
    "aws_key": re.compile(
        r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"
    ),

    # GitHub Personal Access Token
    "github_token": re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}\b"
    ),

    # Stripe API Key
    "stripe_key": re.compile(
        r"\b(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]{24,}\b"
    ),
}


# Mapping from pattern name to PIIType
PATTERN_TO_TYPE: Final[dict[str, str]] = {
    "email": "email",
    "phone_us": "phone_us",
    "phone_intl": "phone_intl",
    "ssn": "ssn",
    "credit_card": "credit_card",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "aws_key": "aws_key",
    "github_token": "github_token",
    "stripe_key": "stripe_key",
}


# Patterns enabled at each sensitivity level
SENSITIVITY_PATTERNS: Final[dict[str, list[str]]] = {
    "low": ["email"],
    "medium": ["email", "phone_us", "phone_intl", "ssn", "credit_card"],
    "high": [
        "email", "phone_us", "phone_intl", "ssn", "credit_card",
        "ipv4", "ipv6", "aws_key", "github_token", "stripe_key"
    ],
    "maximum": [
        "email", "phone_us", "phone_intl", "ssn", "credit_card",
        "ipv4", "ipv6", "aws_key", "github_token", "stripe_key"
    ],  # Plus Presidio NER
}
```

### 2.4 Detector Implementation (detector.py)

```python
"""PII Detection service for pre-embedding content screening.

This service scans text for PII patterns and returns metadata flags
WITHOUT storing or logging the actual PII values.
"""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.services.pii.patterns import (
    PII_PATTERNS,
    PATTERN_TO_TYPE,
    SENSITIVITY_PATTERNS,
)
from app.services.pii.types import PIIMatch, PIIResult, PIIType, SensitivityLevel

logger = structlog.get_logger(__name__)


class PIIDetector:
    """Detects PII in text using regex patterns.

    IMPORTANT: This detector never stores or logs actual PII values.
    It only returns type flags and counts for metadata.
    """

    def __init__(
        self,
        sensitivity: SensitivityLevel | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Initialize the PII detector.

        Args:
            sensitivity: Detection sensitivity level. Defaults to config.
            enabled: Whether detection is enabled. Defaults to config.

        """
        self.sensitivity = sensitivity or SensitivityLevel(
            getattr(settings, "PII_SENSITIVITY_LEVEL", "medium")
        )
        self.enabled = enabled if enabled is not None else getattr(
            settings, "PII_SCREENING_ENABLED", False
        )

        # Get patterns for this sensitivity level
        pattern_names = SENSITIVITY_PATTERNS.get(self.sensitivity.value, [])
        self.active_patterns = {
            name: PII_PATTERNS[name]
            for name in pattern_names
            if name in PII_PATTERNS
        }

        logger.info(
            "pii_detector_initialized",
            enabled=self.enabled,
            sensitivity=self.sensitivity.value,
            pattern_count=len(self.active_patterns),
        )

    def scan(self, text: str) -> PIIResult:
        """Scan text for PII patterns.

        Args:
            text: The text content to scan.

        Returns:
            PIIResult with detection flags (no actual PII values).

        """
        if not self.enabled:
            return PIIResult(has_pii=False)

        if not text or not text.strip():
            return PIIResult(has_pii=False)

        matches: list[PIIMatch] = []
        types_found: set[PIIType] = set()
        matches_by_type: dict[PIIType, int] = {}

        for pattern_name, pattern in self.active_patterns.items():
            pii_type = PIIType(PATTERN_TO_TYPE[pattern_name])

            for match in pattern.finditer(text):
                # Store match metadata, NOT the value
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    start=match.start(),
                    end=match.end(),
                ))
                types_found.add(pii_type)
                matches_by_type[pii_type] = matches_by_type.get(pii_type, 0) + 1

        has_pii = len(matches) > 0

        if has_pii:
            # Log detection event WITHOUT values
            logger.warning(
                "pii_detected",
                pii_types=[t.value for t in types_found],
                match_count=len(matches),
                # NEVER log: actual values, offsets that could reveal content
            )

        return PIIResult(
            has_pii=has_pii,
            types=list(types_found),
            match_count=len(matches),
            matches_by_type=matches_by_type,
        )

    def scan_chunks(
        self,
        chunks: list[str],
    ) -> tuple[list[PIIResult], int, int]:
        """Scan multiple chunks for PII.

        Args:
            chunks: List of text chunks to scan.

        Returns:
            Tuple of (results, clean_count, flagged_count).

        """
        results = [self.scan(chunk) for chunk in chunks]
        flagged_count = sum(1 for r in results if r.has_pii)
        clean_count = len(results) - flagged_count

        if flagged_count > 0:
            logger.info(
                "pii_batch_scan_complete",
                total_chunks=len(chunks),
                flagged_count=flagged_count,
                clean_count=clean_count,
            )

        return results, clean_count, flagged_count


# Singleton instance
_detector: PIIDetector | None = None


def get_pii_detector() -> PIIDetector:
    """Get the singleton PII detector instance."""
    global _detector
    if _detector is None:
        _detector = PIIDetector()
    return _detector
```

---

## 3. Pipeline Integration

### 3.1 Modified chunk_content.py

```python
"""Chunk content workflow task with PII screening."""

from app.core.config import settings
from app.services.pii.detector import get_pii_detector
from app.services.pii.types import PIIAction
from app.workflows.state import AnalysisState


class PIIRejectError(ValueError):
    """Raised when content is rejected due to PII detection."""

    def __init__(self, pii_types: list[str]) -> None:
        self.pii_types = pii_types
        super().__init__(f"Content rejected: PII detected ({', '.join(pii_types)})")


async def chunk_content(state: AnalysisState) -> dict:
    """Chunk content with optional PII screening.

    Flow:
    1. If PII screening enabled, scan raw content
    2. If PII found and action=reject, raise PIIRejectError
    3. If PII found and action=flag, add metadata to state
    4. Proceed with existing chunking logic

    """
    text = state["raw_content"]
    pii_metadata: dict = {"pii_flag": False, "pii_types": []}

    # PII Screening (Issue #220)
    if getattr(settings, "PII_SCREENING_ENABLED", False):
        detector = get_pii_detector()
        pii_result = detector.scan(text)

        if pii_result.has_pii:
            pii_metadata = pii_result.to_metadata()

            # Check if we should reject
            action = getattr(settings, "PII_ACTION", PIIAction.FLAG)
            if action == PIIAction.REJECT or pii_result.should_reject:
                raise PIIRejectError(pii_types=[t.value for t in pii_result.types])

    # Store PII metadata in state for downstream storage
    state["pii_metadata"] = pii_metadata

    # ... existing chunking logic continues ...
    # The pii_metadata will be propagated to store_embeddings
```

### 3.2 Modified store_embeddings.py

```python
"""Store embeddings with PII metadata."""

async def store_embeddings(state: AnalysisState) -> dict:
    """Store chunk embeddings with PII flags."""

    pii_metadata = state.get("pii_metadata", {"pii_flag": False, "pii_types": []})

    for chunk in chunks:
        repo_item = {
            "analysis_id": analysis_id,
            "snippet": chunk.text[:200],
            "granularity": chunk.granularity,
            "vector": embedding,
            # ... existing fields ...

            # NEW: PII fields (Issue #220)
            "pii_flag": pii_metadata.get("pii_flag", False),
            "pii_types": pii_metadata.get("pii_types", []),
        }
        repo_items.append(repo_item)
```

---

## 4. Cleanup Services

### 4.1 Orphan Cleaner

```python
"""Orphan chunk detection and cleanup service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.models.analysis_chunk import AnalysisChunk

logger = structlog.get_logger(__name__)


class OrphanCleaner:
    """Detects and removes orphan chunks without valid analyses."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_orphans(self, limit: int = 1000) -> list[UUID]:
        """Find chunk IDs without valid parent analyses.

        Uses LEFT JOIN to detect missing foreign key references.
        """
        # Raw SQL for efficiency
        query = text("""
            SELECT c.id
            FROM analysis_chunks c
            LEFT JOIN analyses a ON c.analysis_id = a.id
            WHERE a.id IS NULL
            LIMIT :limit
        """)

        result = await self.session.execute(query, {"limit": limit})
        orphan_ids = [row[0] for row in result.fetchall()]

        if orphan_ids:
            logger.warning(
                "orphan_chunks_detected",
                count=len(orphan_ids),
            )

        return orphan_ids

    async def delete_orphans(self, batch_size: int = 1000) -> int:
        """Delete orphan chunks in batches.

        Returns:
            Total number of orphans deleted.

        """
        total_deleted = 0

        while True:
            orphan_ids = await self.find_orphans(limit=batch_size)
            if not orphan_ids:
                break

            # Delete batch
            delete_query = text("""
                DELETE FROM analysis_chunks
                WHERE id = ANY(:ids)
            """)
            await self.session.execute(delete_query, {"ids": orphan_ids})
            await self.session.commit()

            total_deleted += len(orphan_ids)
            logger.info(
                "orphan_chunks_deleted",
                batch_size=len(orphan_ids),
                total_deleted=total_deleted,
            )

        return total_deleted
```

### 4.2 Integrity Checker

```python
"""Vector integrity checking service."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class IntegrityReport:
    """Report of vector integrity issues."""

    dimension_mismatches: list[UUID]
    null_vectors: list[UUID]
    zero_vectors: list[UUID]
    total_checked: int
    total_issues: int


class IntegrityChecker:
    """Validates vector integrity in the database."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expected_dimensions = settings.EMBEDDING_DIMENSIONS

    async def check_all(self, limit: int = 10000) -> IntegrityReport:
        """Run all integrity checks and return report."""

        dimension_mismatches = await self._check_dimensions(limit)
        null_vectors = await self._check_null_vectors(limit)
        zero_vectors = await self._check_zero_vectors(limit)

        total_issues = (
            len(dimension_mismatches) +
            len(null_vectors) +
            len(zero_vectors)
        )

        report = IntegrityReport(
            dimension_mismatches=dimension_mismatches,
            null_vectors=null_vectors,
            zero_vectors=zero_vectors,
            total_checked=limit,
            total_issues=total_issues,
        )

        if total_issues > 0:
            logger.warning(
                "vector_integrity_issues",
                dimension_mismatches=len(dimension_mismatches),
                null_vectors=len(null_vectors),
                zero_vectors=len(zero_vectors),
            )

        return report

    async def _check_dimensions(self, limit: int) -> list[UUID]:
        """Find vectors with wrong dimensions."""
        query = text("""
            SELECT id FROM analysis_chunks
            WHERE vector IS NOT NULL
            AND array_length(vector::float[], 1) != :expected
            LIMIT :limit
        """)
        result = await self.session.execute(
            query, {"expected": self.expected_dimensions, "limit": limit}
        )
        return [row[0] for row in result.fetchall()]

    async def _check_null_vectors(self, limit: int) -> list[UUID]:
        """Find chunks that should have vectors but don't."""
        query = text("""
            SELECT id FROM analysis_chunks
            WHERE vector IS NULL
            AND granularity IN ('coarse', 'fine')
            LIMIT :limit
        """)
        result = await self.session.execute(query, {"limit": limit})
        return [row[0] for row in result.fetchall()]

    async def _check_zero_vectors(self, limit: int) -> list[UUID]:
        """Find zero vectors (all elements near zero)."""
        # Using L2 norm approximation
        query = text("""
            SELECT id FROM analysis_chunks
            WHERE vector IS NOT NULL
            AND (
                SELECT sqrt(sum(v * v))
                FROM unnest(vector::float[]) AS v
            ) < :threshold
            LIMIT :limit
        """)
        result = await self.session.execute(
            query, {"threshold": settings.VECTOR_ZERO_THRESHOLD, "limit": limit}
        )
        return [row[0] for row in result.fetchall()]
```

### 4.3 TTL Manager

```python
"""Draft TTL cleanup service."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


class TTLManager:
    """Manages TTL-based cleanup of draft analyses."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ttl_days = getattr(settings, "CLEANUP_DRAFT_TTL_DAYS", 7)

    async def find_expired_drafts(self, limit: int = 1000) -> list[str]:
        """Find draft analyses older than TTL."""
        cutoff = datetime.utcnow() - timedelta(days=self.ttl_days)

        query = text("""
            SELECT id FROM analyses
            WHERE status = 'draft'
            AND created_at < :cutoff
            LIMIT :limit
        """)
        result = await self.session.execute(
            query, {"cutoff": cutoff, "limit": limit}
        )
        return [str(row[0]) for row in result.fetchall()]

    async def delete_expired_drafts(self, batch_size: int = 100) -> int:
        """Delete expired drafts (cascades to chunks).

        Returns:
            Number of analyses deleted.

        """
        total_deleted = 0

        while True:
            expired_ids = await self.find_expired_drafts(limit=batch_size)
            if not expired_ids:
                break

            # Delete analyses (FK cascade deletes chunks)
            delete_query = text("""
                DELETE FROM analyses
                WHERE id = ANY(:ids)
            """)
            await self.session.execute(delete_query, {"ids": expired_ids})
            await self.session.commit()

            total_deleted += len(expired_ids)
            logger.info(
                "expired_drafts_deleted",
                batch_size=len(expired_ids),
                total_deleted=total_deleted,
            )

        return total_deleted
```

---

## 5. Database Schema

### 5.1 Migration Script

```python
"""Add PII columns to analysis_chunks.

Revision ID: 20251210_add_pii_columns
Revises: previous_revision
Create Date: 2025-12-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20251210_add_pii_columns"
down_revision = "previous_revision"  # Update to actual revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add PII flag column
    op.add_column(
        "analysis_chunks",
        sa.Column("pii_flag", sa.Boolean(), nullable=True, server_default="false"),
    )

    # Add PII types JSONB column
    op.add_column(
        "analysis_chunks",
        sa.Column("pii_types", JSONB(), nullable=True),
    )

    # Partial index for efficient PII queries
    op.create_index(
        "ix_analysis_chunks_pii_flag",
        "analysis_chunks",
        ["pii_flag"],
        postgresql_where=sa.text("pii_flag = true"),
    )

    # Index for analysis_id (if not exists) for orphan detection
    op.create_index(
        "ix_analysis_chunks_analysis_id",
        "analysis_chunks",
        ["analysis_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_chunks_pii_flag")
    op.drop_column("analysis_chunks", "pii_types")
    op.drop_column("analysis_chunks", "pii_flag")
```

### 5.2 Model Changes

```python
# In analysis_chunk.py, add:

class AnalysisChunk(Base):
    # ... existing columns ...

    # PII metadata (Issue #220)
    pii_flag: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=True,
        doc="Whether PII was detected in this chunk",
    )
    pii_types: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Types of PII detected (e.g., ['email', 'phone'])",
    )
```

---

## 6. Configuration

### 6.1 Config Settings

```python
# In config.py, add:

class Settings(BaseSettings):
    # ... existing settings ...

    # PII Screening Configuration (Issue #220)
    PII_SCREENING_ENABLED: bool = Field(
        default=False,
        description="Enable PII detection before embedding",
    )
    PII_SENSITIVITY_LEVEL: str = Field(
        default="medium",
        description="Detection sensitivity: low, medium, high, maximum",
    )
    PII_ACTION: str = Field(
        default="flag",
        description="Action on PII detection: flag (continue) or reject (fail)",
    )
    PII_REJECT_THRESHOLD: float = Field(
        default=0.3,
        description="Reject if PII density exceeds this threshold (0.0-1.0)",
    )
    PII_USE_PRESIDIO: bool = Field(
        default=False,
        description="Enable Presidio for NER-based PII detection",
    )

    # Cleanup Configuration (Issue #220)
    CLEANUP_ENABLED: bool = Field(
        default=True,
        description="Enable scheduled cleanup jobs",
    )
    CLEANUP_DRAFT_TTL_DAYS: int = Field(
        default=7,
        description="Days before draft analyses are deleted",
    )
    CLEANUP_BATCH_SIZE: int = Field(
        default=1000,
        description="Batch size for cleanup operations",
    )
```

---

## 7. API Contracts

### 7.1 PIIResult Schema

```python
# For potential API exposure

class PIIResultSchema(BaseModel):
    """Schema for PII detection results."""

    has_pii: bool
    pii_types: list[str]
    match_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "has_pii": True,
                "pii_types": ["email", "phone_us"],
                "match_count": 5,
            }
        }
```

### 7.2 Cleanup Endpoints (Optional)

```python
# Optional API endpoints for manual cleanup

@router.post("/admin/cleanup/orphans")
async def cleanup_orphans(
    db: AsyncSession = Depends(get_db),
    admin_key: str = Header(...),
) -> dict:
    """Manually trigger orphan cleanup."""
    cleaner = OrphanCleaner(db)
    deleted = await cleaner.delete_orphans()
    return {"deleted_count": deleted}


@router.get("/admin/integrity/report")
async def get_integrity_report(
    db: AsyncSession = Depends(get_db),
    admin_key: str = Header(...),
) -> IntegrityReport:
    """Get vector integrity report."""
    checker = IntegrityChecker(db)
    return await checker.check_all()
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/services/pii/test_detector.py

import pytest
from app.services.pii.detector import PIIDetector
from app.services.pii.types import PIIType, SensitivityLevel


class TestPIIDetector:
    """Unit tests for PII detection."""

    def test_detects_email(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.LOW, enabled=True)
        result = detector.scan("Contact us at test@example.com for info")
        assert result.has_pii
        assert PIIType.EMAIL in result.types

    def test_detects_phone_us(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.MEDIUM, enabled=True)
        result = detector.scan("Call us at (555) 123-4567")
        assert result.has_pii
        assert PIIType.PHONE_US in result.types

    def test_detects_ssn(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.MEDIUM, enabled=True)
        result = detector.scan("SSN: 123-45-6789")
        assert result.has_pii
        assert PIIType.SSN in result.types

    def test_detects_credit_card(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.MEDIUM, enabled=True)
        result = detector.scan("Card: 4111111111111111")
        assert result.has_pii
        assert PIIType.CREDIT_CARD in result.types

    def test_no_pii_in_clean_text(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)
        result = detector.scan("This is clean technical documentation.")
        assert not result.has_pii
        assert len(result.types) == 0

    def test_disabled_returns_no_pii(self):
        detector = PIIDetector(enabled=False)
        result = detector.scan("test@example.com")
        assert not result.has_pii

    def test_multiple_pii_types(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)
        result = detector.scan(
            "Contact: test@example.com, Phone: 555-123-4567, IP: 192.168.1.1"
        )
        assert result.has_pii
        assert PIIType.EMAIL in result.types
        assert PIIType.PHONE_US in result.types
        assert PIIType.IPV4 in result.types
        assert result.match_count == 3

    def test_api_key_detection(self):
        detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)
        result = detector.scan("AWS Key: AKIAIOSFODNN7EXAMPLE")
        assert result.has_pii
        assert PIIType.AWS_KEY in result.types

    def test_to_metadata_no_values(self):
        """Ensure metadata doesn't contain actual PII values."""
        detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)
        result = detector.scan("Email: secret@company.com")
        metadata = result.to_metadata()

        assert "secret@company.com" not in str(metadata)
        assert metadata["pii_flag"] is True
        assert "email" in metadata["pii_types"]
```

### 8.2 Integration Tests

```python
# tests/integration/services/test_pii_pipeline.py

@pytest.mark.asyncio
async def test_pii_flagged_in_stored_chunk(db_session, settings_with_pii):
    """Verify PII flags are stored in database."""
    settings_with_pii.PII_SCREENING_ENABLED = True
    settings_with_pii.PII_ACTION = "flag"

    # Create analysis with PII content
    content = "Contact: test@example.com"
    result = await run_embedding_pipeline(content, db_session)

    # Verify chunk has PII flag
    chunks = await get_chunks_for_analysis(result.analysis_id, db_session)
    assert any(c.pii_flag for c in chunks)
    assert "email" in chunks[0].pii_types


@pytest.mark.asyncio
async def test_pii_reject_stops_pipeline(db_session, settings_with_pii):
    """Verify PII rejection stops the pipeline."""
    settings_with_pii.PII_SCREENING_ENABLED = True
    settings_with_pii.PII_ACTION = "reject"

    with pytest.raises(PIIRejectError):
        await run_embedding_pipeline("SSN: 123-45-6789", db_session)
```

---

**Document Version:** 1.0
**Last Updated:** December 10, 2025
