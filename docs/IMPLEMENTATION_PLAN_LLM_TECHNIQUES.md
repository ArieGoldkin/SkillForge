# Implementation Plan: Advanced LLM Techniques

> **SkillForge Multi-Agent Analysis System Enhancement**
>
> Document Version: 1.0 | Created: 2025-12-16 | Status: READY FOR REVIEW

---

## Executive Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION OVERVIEW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TIMELINE:        12-16 weeks (3-4 months)                                  │
│  PHASES:          5 phases + prerequisites                                   │
│  TEAM:            1-2 backend engineers                                      │
│  RISK:            Low-Medium (feature-flagged, incremental)                 │
│                                                                              │
│  EXPECTED OUTCOMES:                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Metric              │ Current    │ Target     │ Improvement           │ │
│  │──────────────────────┼────────────┼────────────┼──────────────────────│ │
│  │  Quality Score       │ 0.72       │ 0.90+      │ +25-35%               │ │
│  │  Cost per Analysis   │ $0.528     │ $0.05-0.10 │ -80-90%               │ │
│  │  Avg Latency         │ 45s        │ 15-25s     │ -45-65%               │ │
│  │  Cache Hit Rate      │ 0%         │ 50-70%     │ N/A (new)             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 0: Infrastructure Setup](#phase-0-infrastructure-setup)
3. [Phase 1: Few-Shot Prompting](#phase-1-few-shot-prompting)
4. [Phase 2: Chain-of-Thought Supervisor](#phase-2-chain-of-thought-supervisor)
5. [Phase 3: Double Caching (Redis + Claude)](#phase-3-double-caching-redis--claude)
6. [Phase 4: Simplified Tree-of-Thoughts](#phase-4-simplified-tree-of-thoughts)
7. [Phase 5: ReAct Enhancement](#phase-5-react-enhancement)
8. [Dependency Graph](#dependency-graph)
9. [Risk Mitigation](#risk-mitigation)
10. [Rollback Procedures](#rollback-procedures)
11. [Success Metrics & Monitoring](#success-metrics--monitoring)

---

## Prerequisites

### System Requirements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PREREQUISITES CHECKLIST                              │
└─────────────────────────────────────────────────────────────────────────────┘

[x] PostgreSQL 17 with PGVector extension (existing)
[x] Python 3.11+ with Poetry (existing)
[x] LangChain + LangGraph installed (existing)
[x] LangSmith account for observability (existing)
[x] Golden Dataset: 98 curated analyses (existing)

[ ] Redis Stack 7.4+ (NEW - Phase 3)
[ ] redisvl>=0.3.0 package (NEW - Phase 3)
[ ] langchain-redis>=0.1.0 package (NEW - Phase 3)
```

### New Dependencies to Add

```toml
# backend/pyproject.toml - additions

[tool.poetry.dependencies]
# Phase 1: Few-Shot
# No new dependencies (uses existing PGVector)

# Phase 3: Redis Caching
redis = "^5.0.0"
redisvl = "^0.3.0"
langchain-redis = "^0.1.0"
```

### Environment Variables to Add

```bash
# backend/.env - additions

# Phase 1: Few-Shot
ENABLE_FEW_SHOT=false
FEW_SHOT_MAX_EXAMPLES=3
FEW_SHOT_MIN_QUALITY=0.8

# Phase 2: CoT Supervisor
ENABLE_COT_SUPERVISOR=false
COT_CONTENT_THRESHOLD=5000
COT_REASONING_MODEL=claude-sonnet-4-20250514

# Phase 3: Caching
ENABLE_REDIS_CACHE=false
REDIS_URL=redis://localhost:6379
REDIS_CACHE_TTL=86400
REDIS_SIMILARITY_THRESHOLD=0.92
ENABLE_PROMPT_CACHING=false
PROMPT_CACHE_TTL=300

# Phase 4: ToT
ENABLE_TOT_RESOLVER=false
TOT_CONFLICT_THRESHOLD=0.3

# Phase 5: ReAct
ENABLE_REACT_TRACING=false
REACT_MAX_ITERATIONS=5
```

---

## Phase 0: Infrastructure Setup

**Duration:** 1 week | **Risk:** Low | **Dependencies:** None

### 0.1 Create Feature Flag System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/core/feature_flags.py                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
# backend/app/core/feature_flags.py

"""Feature flags for advanced LLM techniques.

All techniques are disabled by default and enabled via environment variables.
This allows gradual rollout and instant rollback.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class TechniqueFlags(BaseSettings):
    """Feature flags for LLM techniques."""

    # Phase 1: Few-Shot Prompting
    enable_few_shot: bool = False
    few_shot_max_examples: int = 3
    few_shot_min_quality: float = 0.8
    few_shot_use_semantic: bool = True

    # Phase 2: CoT Supervisor
    enable_cot_supervisor: bool = False
    cot_content_threshold: int = 5000
    cot_reasoning_model: str = "claude-sonnet-4-20250514"

    # Phase 3: Caching
    enable_redis_cache: bool = False
    redis_url: str = "redis://localhost:6379"
    redis_cache_ttl: int = 86400
    redis_similarity_threshold: float = 0.92
    enable_prompt_caching: bool = False
    prompt_cache_ttl: int = 300

    # Phase 4: ToT
    enable_tot_resolver: bool = False
    tot_conflict_threshold: float = 0.3

    # Phase 5: ReAct
    enable_react_tracing: bool = False
    react_max_iterations: int = 5

    # A/B Testing
    ab_test_enabled: bool = False
    ab_test_treatment_pct: float = 0.2  # 20% traffic

    class Config:
        env_prefix = "TECHNIQUE_"
        env_file = ".env"


@lru_cache
def get_technique_flags() -> TechniqueFlags:
    """Get cached technique flags."""
    return TechniqueFlags()


def is_treatment_group(analysis_id: str) -> bool:
    """Determine if analysis should use experimental features (A/B test)."""
    flags = get_technique_flags()
    if not flags.ab_test_enabled:
        return False

    # Deterministic assignment based on analysis_id hash
    hash_value = hash(analysis_id) % 100
    return hash_value < (flags.ab_test_treatment_pct * 100)
```

### 0.2 Create Metrics Tracking

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/shared/services/metrics/technique_metrics.py             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
# backend/app/shared/services/metrics/technique_metrics.py

"""Metrics tracking for LLM technique performance."""

import time
from dataclasses import dataclass, field
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TechniqueMetrics:
    """Metrics for a single analysis run."""

    analysis_id: str
    technique: str
    variant: Literal["control", "treatment"]

    # Performance
    latency_ms: float = 0
    token_count_input: int = 0
    token_count_output: int = 0

    # Caching
    cache_hit: bool = False
    cache_level: str | None = None  # "l1_exact", "l2_redis", "l3_prompt"

    # Quality (populated later via feedback)
    quality_score: float | None = None

    # Cost
    estimated_cost_usd: float = 0

    # Timestamps
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class MetricsCollector:
    """Collect and report technique metrics."""

    def __init__(self):
        self._metrics: list[TechniqueMetrics] = []

    def record(self, metrics: TechniqueMetrics) -> None:
        """Record metrics for an analysis."""
        metrics.completed_at = time.time()
        self._metrics.append(metrics)

        logger.info(
            "technique_metrics_recorded",
            analysis_id=metrics.analysis_id,
            technique=metrics.technique,
            variant=metrics.variant,
            latency_ms=metrics.latency_ms,
            cache_hit=metrics.cache_hit,
            estimated_cost_usd=metrics.estimated_cost_usd,
        )

    def get_summary(self, technique: str) -> dict:
        """Get summary statistics for a technique."""
        technique_metrics = [m for m in self._metrics if m.technique == technique]

        if not technique_metrics:
            return {}

        control = [m for m in technique_metrics if m.variant == "control"]
        treatment = [m for m in technique_metrics if m.variant == "treatment"]

        return {
            "technique": technique,
            "control_count": len(control),
            "treatment_count": len(treatment),
            "control_avg_latency": sum(m.latency_ms for m in control) / len(control) if control else 0,
            "treatment_avg_latency": sum(m.latency_ms for m in treatment) / len(treatment) if treatment else 0,
            "treatment_cache_hit_rate": sum(1 for m in treatment if m.cache_hit) / len(treatment) if treatment else 0,
        }


# Global collector instance
metrics_collector = MetricsCollector()
```

### 0.3 File Structure Setup

```bash
# Create directory structure for new modules

mkdir -p backend/app/domains/analysis/workflows/agents/techniques
mkdir -p backend/app/domains/analysis/workflows/agents/prompts/examples
mkdir -p backend/app/domains/analysis/workflows/nodes/supervisor
mkdir -p backend/app/domains/analysis/workflows/tasks/aggregation/conflict_resolution
mkdir -p backend/app/shared/services/cache
mkdir -p backend/app/shared/services/metrics

# Create __init__.py files
touch backend/app/domains/analysis/workflows/agents/techniques/__init__.py
touch backend/app/domains/analysis/workflows/agents/prompts/__init__.py
touch backend/app/domains/analysis/workflows/agents/prompts/examples/__init__.py
touch backend/app/domains/analysis/workflows/nodes/supervisor/__init__.py
touch backend/app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/__init__.py
touch backend/app/shared/services/cache/__init__.py
touch backend/app/shared/services/metrics/__init__.py
```

### Phase 0 Deliverables

| Deliverable | File | Status |
|-------------|------|--------|
| Feature flag system | `core/feature_flags.py` | To implement |
| Metrics collector | `shared/services/metrics/technique_metrics.py` | To implement |
| Directory structure | Multiple | To create |
| Environment variables | `.env.example` | To update |

---

## Phase 1: Few-Shot Prompting

**Duration:** 2-3 weeks | **Risk:** Low | **Dependencies:** Phase 0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: FEW-SHOT PROMPTING                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GOAL: Improve agent output quality by 15-25% through example injection     │
│                                                                              │
│  APPROACH:                                                                   │
│  1. Store high-quality examples from golden dataset in new table            │
│  2. Use semantic similarity (PGVector) to find relevant examples            │
│  3. Inject 3-6 examples into agent prompts                                  │
│  4. A/B test and measure quality improvement                                │
│                                                                              │
│  FILES TO CREATE:                                                           │
│  ├─ alembic/versions/xxx_add_agent_examples.py                              │
│  ├─ app/models/agent_example.py                                             │
│  ├─ app/db/repositories/agent_examples.py                                   │
│  ├─ app/domains/analysis/workflows/agents/techniques/few_shot.py            │
│  ├─ app/domains/analysis/workflows/agents/prompts/examples/*.json           │
│  └─ scripts/seed_few_shot_examples.py                                       │
│                                                                              │
│  FILES TO MODIFY:                                                           │
│  ├─ app/domains/analysis/workflows/agents/prompt_builders.py                │
│  └─ app/domains/analysis/workflows/agents/base.py                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Database Migration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/alembic/versions/xxx_add_agent_examples.py                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Add agent_examples table for few-shot prompting.

Revision ID: xxx_add_agent_examples
Revises: <previous_revision>
Create Date: 2025-12-16
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "xxx_add_agent_examples"
down_revision = "<previous_revision>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_examples",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),

        # Few-shot data
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("input_content_preview", sa.Text(), nullable=True),  # First 2000 chars
        sa.Column("output_example", sa.JSON(), nullable=False),
        sa.Column("context_note", sa.Text(), nullable=True),

        # Quality metadata
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_golden", sa.Boolean(), server_default="false"),
        sa.Column("source_analysis_id", sa.UUID(), nullable=True),

        # Semantic search
        sa.Column("embedding", Vector(1536), nullable=True),

        # Content classification
        sa.Column("content_type", sa.String(50), nullable=True),  # article, video, repo
        sa.Column("difficulty_level", sa.String(20), nullable=True),  # beginner, intermediate, advanced

        # Auditing
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),

        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for efficient querying
    op.create_index("idx_agent_examples_type", "agent_examples", ["agent_type"])
    op.create_index("idx_agent_examples_quality", "agent_examples", ["quality_score"])
    op.create_index("idx_agent_examples_content_type", "agent_examples", ["content_type"])

    # Vector index for semantic search (IVFFlat for speed)
    op.execute("""
        CREATE INDEX idx_agent_examples_embedding
        ON agent_examples
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.drop_index("idx_agent_examples_embedding")
    op.drop_index("idx_agent_examples_content_type")
    op.drop_index("idx_agent_examples_quality")
    op.drop_index("idx_agent_examples_type")
    op.drop_table("agent_examples")
```

### 1.2 SQLAlchemy Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/models/agent_example.py                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""SQLAlchemy model for agent few-shot examples."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentExample(Base):
    """Store high-quality agent outputs for few-shot prompting."""

    __tablename__ = "agent_examples"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Few-shot data
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    input_content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_example: Mapped[dict] = mapped_column(JSON, nullable=False)
    context_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality metadata
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False)
    source_analysis_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Semantic search
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Content classification
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Auditing
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default="NOW()", onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AgentExample {self.agent_type}:{self.id}>"
```

### 1.3 Repository Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/db/repositories/agent_examples.py                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Repository for agent example CRUD operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_example import AgentExample
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentExampleRepository:
    """Repository for few-shot example operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_agent_type(
        self,
        agent_type: str,
        min_quality: float = 0.8,
        limit: int = 10,
    ) -> list[AgentExample]:
        """Get high-quality examples for an agent type."""
        stmt = (
            select(AgentExample)
            .where(AgentExample.agent_type == agent_type)
            .where(AgentExample.quality_score >= min_quality)
            .order_by(AgentExample.quality_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_similar_examples(
        self,
        embedding: list[float],
        agent_type: str,
        content_type: str | None = None,
        min_quality: float = 0.8,
        limit: int = 5,
    ) -> list[tuple[AgentExample, float]]:
        """Get semantically similar examples using vector search.

        Returns list of (example, distance) tuples sorted by similarity.
        """
        # Build base query with vector similarity
        stmt = (
            select(
                AgentExample,
                AgentExample.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(AgentExample.agent_type == agent_type)
            .where(AgentExample.quality_score >= min_quality)
            .where(AgentExample.embedding.isnot(None))
        )

        # Optional content type filter
        if content_type:
            stmt = stmt.where(AgentExample.content_type == content_type)

        # Order by similarity (smaller distance = more similar)
        stmt = stmt.order_by("distance").limit(limit)

        result = await self.session.execute(stmt)
        return [(row.AgentExample, row.distance) for row in result]

    async def create(self, example: AgentExample) -> AgentExample:
        """Create a new example."""
        self.session.add(example)
        await self.session.commit()
        await self.session.refresh(example)
        return example

    async def bulk_create(self, examples: list[AgentExample]) -> list[AgentExample]:
        """Create multiple examples."""
        self.session.add_all(examples)
        await self.session.commit()
        return examples

    async def count_by_agent_type(self) -> dict[str, int]:
        """Get count of examples per agent type."""
        from sqlalchemy import func

        stmt = (
            select(AgentExample.agent_type, func.count(AgentExample.id))
            .group_by(AgentExample.agent_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result}
```

### 1.4 Few-Shot Selector

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/workflows/agents/techniques/few_shot.py │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Few-shot example selection and formatting."""

from dataclasses import dataclass
from functools import lru_cache
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger
from app.db.repositories.agent_examples import AgentExampleRepository
from app.shared.services.embedding import EmbeddingService

logger = get_logger(__name__)


@dataclass
class FewShotExample:
    """A formatted few-shot example."""

    input_summary: str
    output_json: dict
    quality_score: float
    distance: float | None = None  # Semantic distance (if applicable)


class FewShotSelector:
    """Select and format few-shot examples for agent prompts."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
    ):
        self.repo = AgentExampleRepository(session)
        self.embedding_service = embedding_service
        self.flags = get_technique_flags()

    async def select_examples(
        self,
        agent_type: str,
        content: str,
        content_type: str | None = None,
        max_examples: int | None = None,
    ) -> list[FewShotExample]:
        """Select best examples for the given content.

        Strategy:
        1. If semantic search enabled, find similar examples by embedding
        2. Otherwise, use top-quality examples for this agent type
        3. Filter by content_type if provided
        """
        max_examples = max_examples or self.flags.few_shot_max_examples
        min_quality = self.flags.few_shot_min_quality

        if self.flags.few_shot_use_semantic:
            return await self._select_semantic(
                agent_type=agent_type,
                content=content,
                content_type=content_type,
                max_examples=max_examples,
                min_quality=min_quality,
            )
        else:
            return await self._select_by_quality(
                agent_type=agent_type,
                content_type=content_type,
                max_examples=max_examples,
                min_quality=min_quality,
            )

    async def _select_semantic(
        self,
        agent_type: str,
        content: str,
        content_type: str | None,
        max_examples: int,
        min_quality: float,
    ) -> list[FewShotExample]:
        """Select examples by semantic similarity."""
        # Generate embedding for input content (truncated)
        content_preview = content[:2000]
        embedding = await self.embedding_service.embed_text(content_preview)

        # Query similar examples
        results = await self.repo.get_similar_examples(
            embedding=embedding,
            agent_type=agent_type,
            content_type=content_type,
            min_quality=min_quality,
            limit=max_examples * 2,  # Get extra for diversity
        )

        # Convert to FewShotExample and diversify
        examples = [
            FewShotExample(
                input_summary=ex.input_summary,
                output_json=ex.output_example,
                quality_score=ex.quality_score,
                distance=dist,
            )
            for ex, dist in results
        ]

        return self._diversify_selection(examples, max_examples)

    async def _select_by_quality(
        self,
        agent_type: str,
        content_type: str | None,
        max_examples: int,
        min_quality: float,
    ) -> list[FewShotExample]:
        """Select examples by quality score only."""
        results = await self.repo.get_by_agent_type(
            agent_type=agent_type,
            min_quality=min_quality,
            limit=max_examples,
        )

        return [
            FewShotExample(
                input_summary=ex.input_summary,
                output_json=ex.output_example,
                quality_score=ex.quality_score,
            )
            for ex in results
        ]

    def _diversify_selection(
        self,
        examples: list[FewShotExample],
        max_examples: int,
    ) -> list[FewShotExample]:
        """Ensure diversity in selected examples.

        Avoids selecting too-similar examples by checking output structure.
        """
        if len(examples) <= max_examples:
            return examples

        selected = [examples[0]]  # Always include most similar

        for ex in examples[1:]:
            if len(selected) >= max_examples:
                break

            # Check if sufficiently different from selected examples
            is_diverse = all(
                self._is_different(ex, sel)
                for sel in selected
            )

            if is_diverse:
                selected.append(ex)

        # Fill remaining slots if needed
        if len(selected) < max_examples:
            for ex in examples:
                if ex not in selected:
                    selected.append(ex)
                if len(selected) >= max_examples:
                    break

        return selected

    def _is_different(self, ex1: FewShotExample, ex2: FewShotExample) -> bool:
        """Check if two examples are sufficiently different."""
        # Simple heuristic: different if key findings differ significantly
        keys1 = set(ex1.output_json.keys())
        keys2 = set(ex2.output_json.keys())

        # At least 20% different keys
        overlap = len(keys1 & keys2) / max(len(keys1 | keys2), 1)
        return overlap < 0.8

    def format_for_prompt(self, examples: list[FewShotExample]) -> str:
        """Format examples for injection into prompt."""
        if not examples:
            return ""

        formatted_parts = [
            "Here are examples of high-quality analyses for similar content:\n"
        ]

        for i, ex in enumerate(examples, 1):
            formatted_parts.append(f"""
<example_{i}>
<input>
{ex.input_summary}
</input>
<output>
{json.dumps(ex.output_json, indent=2)}
</output>
</example_{i}>
""")

        formatted_parts.append(
            "\nUse these examples as reference for structure and quality. "
            "Now analyze the following content:\n"
        )

        return "\n".join(formatted_parts)
```

### 1.5 Modify Prompt Builders

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/workflows/agents/prompt_builders.py     │
│  (MODIFY existing file)                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
# Add to existing prompt_builders.py

from app.core.feature_flags import get_technique_flags
from app.domains.analysis.workflows.agents.techniques.few_shot import (
    FewShotSelector,
    FewShotExample,
)


async def build_agent_user_prompt_with_examples(
    content: str,
    content_type: str,
    agent_type: str,
    session: AsyncSession,
    embedding_service: EmbeddingService,
    max_length: int = 12000,
    proactive_context: str = "",
) -> str:
    """Build user prompt with few-shot examples if enabled.

    Args:
        content: Full content text
        content_type: Type of content (article, video, repo)
        agent_type: Agent type for example selection
        session: Database session
        embedding_service: Service for embedding generation
        max_length: Maximum content length to include
        proactive_context: Memory context (optional)

    Returns:
        Formatted user prompt string with examples (if enabled)
    """
    flags = get_technique_flags()

    # Base prompt (existing logic)
    content_preview = content[:max_length] if len(content) > max_length else content
    base_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

    # Prepend proactive context if available
    if proactive_context:
        base_prompt = f"{proactive_context}\n---\n\n{base_prompt}"

    # Add few-shot examples if enabled
    if flags.enable_few_shot:
        selector = FewShotSelector(session, embedding_service)
        examples = await selector.select_examples(
            agent_type=agent_type,
            content=content,
            content_type=content_type,
        )

        if examples:
            examples_text = selector.format_for_prompt(examples)
            return f"{examples_text}\n{base_prompt}"

    return base_prompt
```

### 1.6 Seed Script

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/scripts/seed_few_shot_examples.py                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Seed few-shot examples from golden dataset.

Usage:
    poetry run python scripts/seed_few_shot_examples.py

This script:
1. Loads high-quality analyses from golden dataset
2. Extracts agent findings with high confidence scores
3. Creates AgentExample records with embeddings
4. Seeds the agent_examples table
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.agent_example import AgentExample
from app.models.agent_finding import AgentFinding
from app.models.analysis import Analysis
from app.shared.services.embedding import EmbeddingService
from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum confidence score for example inclusion
MIN_CONFIDENCE = 0.8

# Agent types to seed
AGENT_TYPES = [
    "tech_comparator",
    "security_auditor",
    "implementation_planner",
    "integration_feasibility",
    "performance_analyst",
    "code_quality_critic",
    "trend_validator",
    "dependency_mapper",
]


async def seed_from_golden_dataset(session: AsyncSession) -> int:
    """Seed examples from golden dataset analyses."""
    embedding_service = EmbeddingService()

    # Get high-quality agent findings
    stmt = (
        select(AgentFinding, Analysis)
        .join(Analysis, AgentFinding.analysis_id == Analysis.id)
        .where(AgentFinding.confidence_score >= MIN_CONFIDENCE)
        .where(AgentFinding.agent_type.in_(AGENT_TYPES))
    )

    result = await session.execute(stmt)
    findings = result.all()

    logger.info(f"Found {len(findings)} high-quality findings to seed")

    examples_created = 0

    for finding, analysis in findings:
        # Check if example already exists
        existing = await session.execute(
            select(AgentExample)
            .where(AgentExample.source_analysis_id == analysis.id)
            .where(AgentExample.agent_type == finding.agent_type)
        )

        if existing.scalar_one_or_none():
            continue

        # Create input summary
        input_summary = f"Analysis of {analysis.content_type}: {analysis.url[:100]}"

        # Get content preview for embedding
        content_preview = (analysis.extracted_content or "")[:2000]

        # Generate embedding
        try:
            embedding = await embedding_service.embed_text(content_preview)
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            embedding = None

        # Create example
        example = AgentExample(
            agent_type=finding.agent_type,
            input_summary=input_summary,
            input_content_preview=content_preview,
            output_example=finding.findings,
            context_note=f"From golden dataset analysis {analysis.id}",
            quality_score=finding.confidence_score or 0.9,
            is_golden=True,
            source_analysis_id=analysis.id,
            embedding=embedding,
            content_type=analysis.content_type,
        )

        session.add(example)
        examples_created += 1

    await session.commit()
    logger.info(f"Created {examples_created} few-shot examples")

    return examples_created


async def main():
    """Main entry point."""
    async with async_session_factory() as session:
        count = await seed_from_golden_dataset(session)
        print(f"Seeded {count} few-shot examples from golden dataset")


if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 1 Testing Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1 TESTING CHECKLIST                           │
└─────────────────────────────────────────────────────────────────────────────┘

Unit Tests:
[ ] test_few_shot_selector.py
    [ ] test_select_examples_semantic
    [ ] test_select_examples_by_quality
    [ ] test_diversify_selection
    [ ] test_format_for_prompt
    [ ] test_empty_examples

[ ] test_agent_example_repository.py
    [ ] test_get_by_agent_type
    [ ] test_get_similar_examples
    [ ] test_bulk_create

Integration Tests:
[ ] test_few_shot_integration.py
    [ ] test_agent_with_examples_produces_output
    [ ] test_examples_improve_quality (manual eval)

A/B Test Setup:
[ ] Enable TECHNIQUE_AB_TEST_ENABLED=true
[ ] Set TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2
[ ] Set TECHNIQUE_ENABLE_FEW_SHOT=true
[ ] Run 100+ analyses and compare quality scores
```

### Phase 1 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Example retrieval latency | <100ms P95 | Prometheus/logs |
| Quality improvement | >10% | LangSmith feedback comparison |
| No latency regression | <5% increase | End-to-end timing |
| Test coverage | >80% | pytest-cov |

---

## Phase 2: Chain-of-Thought Supervisor

**Duration:** 3-4 weeks | **Risk:** Medium | **Dependencies:** Phase 0, 1

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: CHAIN-OF-THOUGHT SUPERVISOR                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GOAL: Improve agent selection accuracy by 15-25% through explicit          │
│        reasoning before structured output                                    │
│                                                                              │
│  APPROACH:                                                                   │
│  1. Phase 1 (Reasoning): Generate CoT reasoning trace                       │
│  2. Phase 2 (Decision): Convert reasoning to structured AgentSelection      │
│  3. Only activate for content > 5K chars (avoid overhead for simple)        │
│                                                                              │
│  FILES TO CREATE:                                                           │
│  ├─ app/domains/analysis/workflows/nodes/supervisor/cot_reasoning.py        │
│  ├─ app/domains/analysis/workflows/nodes/supervisor/decision_validator.py   │
│  └─ app/domains/analysis/schemas/supervisor/reasoning_log.py                │
│                                                                              │
│  FILES TO MODIFY:                                                           │
│  └─ app/domains/analysis/workflows/nodes/supervisor.py                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Reasoning Log Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/schemas/supervisor/reasoning_log.py     │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Schemas for CoT supervisor reasoning."""

from pydantic import BaseModel, Field


class AgentRelevance(BaseModel):
    """Relevance assessment for a single agent."""

    agent_type: str
    relevance: str = Field(description="HIGH, MEDIUM, or LOW")
    reasoning: str = Field(description="Why this agent is/isn't relevant")


class ReasoningLog(BaseModel):
    """Chain-of-thought reasoning trace from supervisor."""

    content_type_analysis: str = Field(
        description="Analysis of what type of content this is"
    )

    detected_patterns: list[str] = Field(
        description="Key patterns detected (code, security, comparisons, etc.)"
    )

    agent_relevance: list[AgentRelevance] = Field(
        description="Relevance assessment for each potential agent"
    )

    preliminary_selection: list[str] = Field(
        description="Initial list of recommended agents"
    )

    confidence_assessment: str = Field(
        description="Overall confidence in the selection (HIGH/MEDIUM/LOW)"
    )

    reasoning_summary: str = Field(
        description="Brief summary of the reasoning process"
    )
```

### 2.2 CoT Reasoning Module

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/workflows/nodes/supervisor/cot_reasoning.py
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Chain-of-Thought reasoning for supervisor routing."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.core.feature_flags import get_technique_flags
from app.core.model_factory import get_chat_model
from app.core.logging import get_logger
from app.domains.analysis.schemas.supervisor.reasoning_log import ReasoningLog

logger = get_logger(__name__)


COT_REASONING_PROMPT = """You are a content analysis supervisor. Analyze the following content step-by-step to determine which specialized agents should process it.

## Available Agents

1. **tech_comparator** - Compares technologies, frameworks, or approaches
2. **security_auditor** - Identifies security concerns, vulnerabilities, best practices
3. **implementation_planner** - Creates step-by-step implementation guides
4. **integration_feasibility** - Assesses integration with modern tech stacks
5. **performance_analyst** - Analyzes performance implications and optimizations
6. **code_quality_critic** - Reviews code patterns, antipatterns, best practices
7. **trend_validator** - Validates against current (2025+) technology trends
8. **dependency_mapper** - Maps required libraries, dependencies, versions

## Your Task

Analyze the content below and reason through each step:

### Step 1: Content Type Analysis
What type of content is this? (tutorial, documentation, comparison, news, etc.)

### Step 2: Pattern Detection
What key patterns do you see?
- Code blocks or snippets?
- Security-related terms (auth, CVE, encryption)?
- Performance indicators (benchmarks, latency)?
- Technology comparisons (vs, compared to, alternatives)?
- Implementation steps or tutorials?
- Dependency/package references?

### Step 3: Agent Relevance Assessment
For EACH agent, assess:
- Relevance: HIGH / MEDIUM / LOW
- Why: Brief reasoning (1 sentence)

### Step 4: Preliminary Selection
Based on your analysis, which agents should process this content?
List them in priority order.

### Step 5: Confidence Assessment
How confident are you in this selection?
- HIGH (>0.8): Clear signals, obvious routing
- MEDIUM (0.5-0.8): Some ambiguity but reasonable
- LOW (<0.5): Unclear, may need broader coverage

## Content to Analyze

Type: {content_type}

Content:
{content}

---

Now provide your step-by-step reasoning:"""


async def generate_cot_reasoning(
    content: str,
    content_type: str,
    model: Runnable | None = None,
) -> ReasoningLog:
    """Generate Chain-of-Thought reasoning for supervisor routing.

    Args:
        content: The content to analyze
        content_type: Type of content (article, video, repo)
        model: Optional model override (for testing)

    Returns:
        ReasoningLog with structured reasoning trace
    """
    flags = get_technique_flags()

    # Use specified model or default reasoning model
    if model is None:
        model = get_chat_model(
            config={"configurable": {"model": flags.cot_reasoning_model}}
        )

    # Create structured output model
    structured_model = model.with_structured_output(ReasoningLog)

    # Build prompt
    prompt = ChatPromptTemplate.from_template(COT_REASONING_PROMPT)

    # Create chain
    chain = prompt | structured_model

    # Invoke
    result = await chain.ainvoke({
        "content": content[:10000],  # Limit content for reasoning phase
        "content_type": content_type,
    })

    logger.info(
        "cot_reasoning_generated",
        content_type=content_type,
        preliminary_selection=result.preliminary_selection,
        confidence=result.confidence_assessment,
    )

    return result
```

### 2.3 Decision Validator

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/workflows/nodes/supervisor/decision_validator.py
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Validate and convert CoT reasoning to structured decision."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.core.model_factory import get_chat_model
from app.core.logging import get_logger
from app.domains.analysis.schemas.supervisor.reasoning_log import ReasoningLog
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection

logger = get_logger(__name__)


COT_DECISION_PROMPT = """Based on the following reasoning analysis, produce a final agent selection.

## Reasoning Analysis

{reasoning_summary}

## Preliminary Selection

{preliminary_selection}

## Agent Relevance Assessments

{agent_relevance}

## Confidence Level

{confidence_assessment}

---

Now produce the final structured selection. Include:
1. Final list of agents (in priority order)
2. Brief reasoning summary
3. Confidence score (0.0-1.0 based on assessment above)

Ensure the selection is appropriate for the content type and detected patterns."""


async def validate_and_select(
    reasoning: ReasoningLog,
    model: Runnable | None = None,
) -> AgentSelection:
    """Convert CoT reasoning to structured AgentSelection.

    This is a lightweight second phase that:
    1. Validates the reasoning is complete
    2. Converts to structured AgentSelection format
    3. Can use a faster model (lower latency)

    Args:
        reasoning: The CoT reasoning log
        model: Optional model override (default: fast model)

    Returns:
        AgentSelection with final decision
    """
    # Use fast model for decision phase
    if model is None:
        model = get_chat_model(
            config={"configurable": {"model": "gemini-2.5-flash"}}
        )

    # Create structured output model
    structured_model = model.with_structured_output(AgentSelection)

    # Format agent relevance
    agent_relevance_text = "\n".join(
        f"- {ar.agent_type}: {ar.relevance} - {ar.reasoning}"
        for ar in reasoning.agent_relevance
    )

    # Build prompt
    prompt = ChatPromptTemplate.from_template(COT_DECISION_PROMPT)

    # Create chain
    chain = prompt | structured_model

    # Invoke
    result = await chain.ainvoke({
        "reasoning_summary": reasoning.reasoning_summary,
        "preliminary_selection": ", ".join(reasoning.preliminary_selection),
        "agent_relevance": agent_relevance_text,
        "confidence_assessment": reasoning.confidence_assessment,
    })

    logger.info(
        "cot_decision_validated",
        selected_agents=result.agents,
        confidence=result.confidence,
    )

    return result
```

### 2.4 Modify Supervisor Node

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/domains/analysis/workflows/nodes/supervisor.py           │
│  (MODIFY existing file - add CoT path)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
# Add to existing supervisor.py imports
from app.core.feature_flags import get_technique_flags
from app.domains.analysis.workflows.nodes.supervisor.cot_reasoning import (
    generate_cot_reasoning,
)
from app.domains.analysis.workflows.nodes.supervisor.decision_validator import (
    validate_and_select,
)


# Add new function for CoT path
async def supervisor_route_with_cot(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    model_id: str | None = None,
) -> dict[str, object]:
    """Supervisor routing with Chain-of-Thought reasoning.

    Two-phase approach:
    1. Generate CoT reasoning trace (comprehensive analysis)
    2. Convert to structured AgentSelection (fast validation)

    This improves selection accuracy for complex content by forcing
    explicit reasoning before the final decision.
    """
    start_time = time.time()

    logger.info(
        "supervisor_cot_started",
        analysis_id=analysis_id,
        content_length=len(content),
    )

    # Emit SSE: supervisor started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=get_stage_name("supervisor"),
        status="running",
        message="Analyzing content with CoT reasoning...",
    )

    try:
        # Phase 1: Generate CoT reasoning
        reasoning = await generate_cot_reasoning(
            content=content,
            content_type=content_type,
        )

        # Phase 2: Validate and produce structured selection
        selection = await validate_and_select(reasoning)

        # ... rest of existing logic (filtering, auto-activation, etc.)

        duration_ms = int((time.time() - start_time) * 1000)

        # Include reasoning trace in decision for debugging
        supervisor_decision = {
            "agents": selection.agents,
            "priority": [selection.confidence] * len(selection.agents),
            "reasoning": selection.reasoning,
            "confidence": selection.confidence,
            "cot_reasoning_trace": reasoning.model_dump(),  # For debugging
        }

        logger.info(
            "supervisor_cot_complete",
            analysis_id=analysis_id,
            selected_agents=selection.agents,
            duration_ms=duration_ms,
        )

        return {"supervisor_decision": supervisor_decision}

    except Exception as e:
        logger.error("supervisor_cot_failed", error=str(e), exc_info=True)
        raise


# Modify existing supervisor_route to use CoT when enabled
async def supervisor_route(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    model_id: str | None = None,
) -> dict[str, object]:
    """Supervisor routing with optional CoT enhancement."""
    flags = get_technique_flags()

    # Use CoT for complex content when enabled
    if (
        flags.enable_cot_supervisor
        and len(content) > flags.cot_content_threshold
    ):
        return await supervisor_route_with_cot(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
            model_id=model_id,
        )

    # Default: existing structured output path
    # ... existing implementation ...
```

### Phase 2 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Agent selection accuracy | +15% | Human evaluation |
| Supervisor latency | <3s P95 | Prometheus |
| Reasoning quality | Useful for debugging | Manual review |
| Test coverage | >80% | pytest-cov |

---

## Phase 3: Double Caching (Redis + Claude)

**Duration:** 3-4 weeks | **Risk:** Medium | **Dependencies:** Phase 0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: DOUBLE CACHING                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GOAL: Reduce costs by 70-90% through multi-level caching                   │
│                                                                              │
│  APPROACH:                                                                   │
│  L1: In-memory LRU cache (exact matches) - ~15% hit rate                    │
│  L2: Redis semantic cache (similar queries) - ~35% hit rate                 │
│  L3: Claude prompt caching (prefix reuse) - always applies                  │
│                                                                              │
│  NEW INFRASTRUCTURE:                                                         │
│  ├─ Redis Stack 7.4+ (docker-compose.yml)                                   │
│  ├─ RedisInsight dashboard (port 8001)                                      │
│  └─ Cache warming from golden dataset                                       │
│                                                                              │
│  FILES TO CREATE:                                                           │
│  ├─ app/shared/services/cache/semantic_cache.py                             │
│  ├─ app/shared/services/cache/prompt_cache.py                               │
│  ├─ app/shared/services/cache/cache_manager.py                              │
│  └─ scripts/warm_redis_cache.py                                             │
│                                                                              │
│  FILES TO MODIFY:                                                           │
│  ├─ docker-compose.yml (add Redis)                                          │
│  ├─ app/core/model_factory.py (add caching layer)                           │
│  └─ app/domains/analysis/workflows/agents/execution.py                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Docker Compose Update

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: docker-compose.yml (MODIFY)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

```yaml
# Add to existing docker-compose.yml

services:
  # ... existing postgres, backend services ...

  redis:
    image: redis/redis-stack:7.4.0-v0
    container_name: skillforge-redis
    ports:
      - "6379:6379"    # Redis
      - "8001:8001"    # RedisInsight UI
    volumes:
      - redis-data:/data
    environment:
      - REDIS_ARGS=--appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-dev-data:
  redis-data:  # Add this
```

### 3.2 Semantic Cache Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/shared/services/cache/semantic_cache.py                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Redis semantic cache for LLM responses."""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from redis import Redis
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger
from app.shared.services.embedding import EmbeddingService

logger = get_logger(__name__)


# Redis index schema for semantic cache
CACHE_INDEX_SCHEMA = {
    "index": {
        "name": "llm_semantic_cache",
        "prefix": "cache:",
    },
    "fields": [
        {"name": "agent_type", "type": "tag"},
        {"name": "content_type", "type": "tag"},
        {"name": "input_hash", "type": "tag"},
        {"name": "embedding", "type": "vector", "attrs": {
            "dims": 1536,
            "distance_metric": "cosine",
            "algorithm": "hnsw",
        }},
        {"name": "response", "type": "text"},
        {"name": "created_at", "type": "numeric"},
        {"name": "hit_count", "type": "numeric"},
        {"name": "quality_score", "type": "numeric"},
    ]
}


@dataclass
class CacheEntry:
    """A cached LLM response."""

    response: dict[str, Any]
    agent_type: str
    content_type: str
    quality_score: float
    created_at: float
    hit_count: int
    distance: float | None = None  # Semantic distance


class SemanticCacheService:
    """Redis-based semantic cache for LLM responses."""

    def __init__(self, redis_url: str | None = None):
        flags = get_technique_flags()
        self.redis_url = redis_url or flags.redis_url
        self.ttl = flags.redis_cache_ttl
        self.similarity_threshold = flags.redis_similarity_threshold

        self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)
        self.embedding_service = EmbeddingService()

        # Initialize search index
        self._init_index()

    def _init_index(self) -> None:
        """Initialize Redis search index."""
        schema = IndexSchema.from_dict(CACHE_INDEX_SCHEMA)
        self.index = SearchIndex(schema, self.redis_client)

        # Create index if not exists
        try:
            self.index.create(overwrite=False)
            logger.info("semantic_cache_index_ready")
        except Exception as e:
            logger.warning(f"Index creation: {e}")

    def _hash_input(self, content: str) -> str:
        """Create hash for exact match lookup."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get(
        self,
        content: str,
        agent_type: str,
        content_type: str | None = None,
    ) -> CacheEntry | None:
        """Look up cached response by semantic similarity.

        Args:
            content: Input content to match
            agent_type: Agent type for filtering
            content_type: Optional content type filter

        Returns:
            CacheEntry if found with sufficient similarity, None otherwise
        """
        start_time = time.time()

        # First try exact hash match (L1 equivalent in Redis)
        input_hash = self._hash_input(content[:2000])
        exact_key = f"cache:{agent_type}:{input_hash}"

        exact_match = self.redis_client.hgetall(exact_key)
        if exact_match:
            # Increment hit count
            self.redis_client.hincrby(exact_key, "hit_count", 1)

            logger.info(
                "semantic_cache_exact_hit",
                agent_type=agent_type,
                latency_ms=int((time.time() - start_time) * 1000),
            )

            return CacheEntry(
                response=json.loads(exact_match["response"]),
                agent_type=agent_type,
                content_type=exact_match.get("content_type", ""),
                quality_score=float(exact_match.get("quality_score", 1.0)),
                created_at=float(exact_match["created_at"]),
                hit_count=int(exact_match["hit_count"]),
                distance=0.0,
            )

        # Semantic search
        embedding = await self.embedding_service.embed_text(content[:2000])

        # Build query with filters
        filter_expr = f"@agent_type:{{{agent_type}}}"
        if content_type:
            filter_expr += f" @content_type:{{{content_type}}}"

        query = VectorQuery(
            vector=embedding,
            vector_field_name="embedding",
            return_fields=["response", "content_type", "quality_score", "created_at", "hit_count"],
            num_results=1,
            filter_expression=filter_expr,
        )

        results = self.index.query(query)

        if results and len(results) > 0:
            result = results[0]
            distance = float(result.get("vector_distance", 1.0))

            # Check similarity threshold
            if distance <= (1 - self.similarity_threshold):
                # Increment hit count
                self.redis_client.hincrby(result["id"], "hit_count", 1)

                logger.info(
                    "semantic_cache_semantic_hit",
                    agent_type=agent_type,
                    distance=distance,
                    latency_ms=int((time.time() - start_time) * 1000),
                )

                return CacheEntry(
                    response=json.loads(result["response"]),
                    agent_type=agent_type,
                    content_type=result.get("content_type", ""),
                    quality_score=float(result.get("quality_score", 1.0)),
                    created_at=float(result["created_at"]),
                    hit_count=int(result["hit_count"]),
                    distance=distance,
                )

        logger.debug(
            "semantic_cache_miss",
            agent_type=agent_type,
            latency_ms=int((time.time() - start_time) * 1000),
        )

        return None

    async def set(
        self,
        content: str,
        response: dict[str, Any],
        agent_type: str,
        content_type: str | None = None,
        quality_score: float = 1.0,
    ) -> None:
        """Store response in cache.

        Args:
            content: Input content (for embedding)
            response: LLM response to cache
            agent_type: Agent type
            content_type: Content type
            quality_score: Quality score (0-1)
        """
        content_preview = content[:2000]
        input_hash = self._hash_input(content_preview)
        embedding = await self.embedding_service.embed_text(content_preview)

        key = f"cache:{agent_type}:{input_hash}"
        now = time.time()

        data = {
            "agent_type": agent_type,
            "content_type": content_type or "",
            "input_hash": input_hash,
            "embedding": embedding,
            "response": json.dumps(response),
            "created_at": now,
            "hit_count": 0,
            "quality_score": quality_score,
        }

        # Store with TTL
        self.redis_client.hset(key, mapping=data)
        self.redis_client.expire(key, self.ttl)

        logger.debug(
            "semantic_cache_stored",
            agent_type=agent_type,
            key=key,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        info = self.redis_client.info("stats")
        keys = self.redis_client.keys("cache:*")

        return {
            "total_entries": len(keys),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) /
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
            ),
            "memory_used_bytes": self.redis_client.info("memory").get("used_memory", 0),
        }

    async def clear_agent(self, agent_type: str) -> int:
        """Clear all cache entries for an agent type."""
        keys = self.redis_client.keys(f"cache:{agent_type}:*")
        if keys:
            return self.redis_client.delete(*keys)
        return 0
```

### 3.3 Prompt Cache Wrapper

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/shared/services/cache/prompt_cache.py                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Claude prompt caching integration."""

from typing import Any

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger

logger = get_logger(__name__)


class PromptCacheManager:
    """Manage Claude prompt caching with cache breakpoints."""

    def __init__(self):
        self.flags = get_technique_flags()

    def build_cached_messages(
        self,
        system_prompt: str,
        few_shot_examples: str | None = None,
        schema_prompt: str | None = None,
        dynamic_content: str = "",
    ) -> list[dict[str, Any]]:
        """Build messages with cache breakpoints for Claude.

        Cache structure:
        1. System prompt (always cached)
        2. Few-shot examples (cached per content type)
        3. Schema documentation (always cached)
        4. Dynamic content (never cached)

        Args:
            system_prompt: Agent system prompt
            few_shot_examples: Optional few-shot examples
            schema_prompt: Optional schema documentation
            dynamic_content: The actual content to analyze

        Returns:
            List of message dicts with cache_control markers
        """
        if not self.flags.enable_prompt_caching:
            # Return simple format without caching
            return [{
                "role": "user",
                "content": f"{system_prompt}\n\n{few_shot_examples or ''}\n\n{dynamic_content}"
            }]

        content_parts = []

        # Breakpoint 1: System prompt (always cached)
        content_parts.append({
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        })

        # Breakpoint 2: Few-shot examples (if provided)
        if few_shot_examples:
            content_parts.append({
                "type": "text",
                "text": few_shot_examples,
                "cache_control": {"type": "ephemeral"}
            })

        # Breakpoint 3: Schema documentation (if provided)
        if schema_prompt:
            content_parts.append({
                "type": "text",
                "text": schema_prompt,
                "cache_control": {"type": "ephemeral"}
            })

        # Dynamic content (NOT cached)
        content_parts.append({
            "type": "text",
            "text": dynamic_content,
        })

        logger.debug(
            "prompt_cache_configured",
            num_breakpoints=len([p for p in content_parts if p.get("cache_control")]),
            cached_tokens_estimate=len(system_prompt + (few_shot_examples or "") + (schema_prompt or "")) // 4,
        )

        return [{
            "role": "user",
            "content": content_parts
        }]
```

### 3.4 Cache Manager

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/app/shared/services/cache/cache_manager.py                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Unified cache manager for multi-level caching."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger
from app.shared.services.cache.semantic_cache import SemanticCacheService, CacheEntry
from app.shared.services.cache.prompt_cache import PromptCacheManager

logger = get_logger(__name__)


CacheLevel = Literal["l1_lru", "l2_redis", "l3_prompt", "l4_none"]


@dataclass
class CacheResult:
    """Result from cache lookup."""

    hit: bool
    level: CacheLevel
    response: dict[str, Any] | None
    latency_ms: float


class CacheManager:
    """Multi-level cache manager.

    Cache hierarchy:
    L1: In-memory LRU (exact match) - fastest, smallest
    L2: Redis semantic cache - fast, medium size
    L3: Claude prompt caching - provider-side
    L4: Full LLM call - no cache
    """

    def __init__(self):
        self.flags = get_technique_flags()
        self.semantic_cache = SemanticCacheService() if self.flags.enable_redis_cache else None
        self.prompt_cache = PromptCacheManager()

        # L1 LRU cache (in-memory)
        self._lru_cache: dict[str, dict[str, Any]] = {}
        self._lru_max_size = 1000

    def _lru_key(self, content: str, agent_type: str) -> str:
        """Generate LRU cache key."""
        import hashlib
        content_hash = hashlib.sha256(content[:2000].encode()).hexdigest()[:16]
        return f"{agent_type}:{content_hash}"

    async def get(
        self,
        content: str,
        agent_type: str,
        content_type: str | None = None,
    ) -> CacheResult:
        """Look up cached response through all cache levels.

        Args:
            content: Input content
            agent_type: Agent type
            content_type: Optional content type

        Returns:
            CacheResult with hit status, level, and response
        """
        import time
        start = time.time()

        # L1: LRU (exact match)
        lru_key = self._lru_key(content, agent_type)
        if lru_key in self._lru_cache:
            latency = (time.time() - start) * 1000
            logger.info("cache_hit_l1", agent_type=agent_type, latency_ms=latency)
            return CacheResult(
                hit=True,
                level="l1_lru",
                response=self._lru_cache[lru_key],
                latency_ms=latency,
            )

        # L2: Redis semantic cache
        if self.semantic_cache:
            entry = await self.semantic_cache.get(
                content=content,
                agent_type=agent_type,
                content_type=content_type,
            )
            if entry:
                # Promote to L1
                self._set_lru(lru_key, entry.response)

                latency = (time.time() - start) * 1000
                logger.info("cache_hit_l2", agent_type=agent_type, latency_ms=latency)
                return CacheResult(
                    hit=True,
                    level="l2_redis",
                    response=entry.response,
                    latency_ms=latency,
                )

        # Cache miss - will use L3 (prompt caching) or L4 (full call)
        latency = (time.time() - start) * 1000
        return CacheResult(
            hit=False,
            level="l4_none",  # Will be L3 if prompt caching enabled
            response=None,
            latency_ms=latency,
        )

    async def set(
        self,
        content: str,
        response: dict[str, Any],
        agent_type: str,
        content_type: str | None = None,
        quality_score: float = 1.0,
    ) -> None:
        """Store response in cache hierarchy.

        Args:
            content: Input content
            response: LLM response
            agent_type: Agent type
            content_type: Content type
            quality_score: Quality score for prioritization
        """
        # L1: LRU
        lru_key = self._lru_key(content, agent_type)
        self._set_lru(lru_key, response)

        # L2: Redis
        if self.semantic_cache:
            await self.semantic_cache.set(
                content=content,
                response=response,
                agent_type=agent_type,
                content_type=content_type,
                quality_score=quality_score,
            )

    def _set_lru(self, key: str, value: dict[str, Any]) -> None:
        """Set value in LRU cache with eviction."""
        # Simple LRU: remove oldest if full
        if len(self._lru_cache) >= self._lru_max_size:
            oldest = next(iter(self._lru_cache))
            del self._lru_cache[oldest]

        self._lru_cache[key] = value

    def get_stats(self) -> dict[str, Any]:
        """Get combined cache statistics."""
        stats = {
            "l1_lru_size": len(self._lru_cache),
            "l1_lru_max_size": self._lru_max_size,
        }

        if self.semantic_cache:
            stats["l2_redis"] = self.semantic_cache.get_stats()

        return stats


# Global instance
@lru_cache
def get_cache_manager() -> CacheManager:
    """Get cached CacheManager instance."""
    return CacheManager()
```

### 3.5 Cache Warming Script

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  File: backend/scripts/warm_redis_cache.py                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

```python
"""Warm Redis cache from golden dataset.

Usage:
    poetry run python scripts/warm_redis_cache.py

This pre-populates the semantic cache with high-quality responses
from the golden dataset, ensuring good hit rates from day one.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.agent_finding import AgentFinding
from app.models.analysis import Analysis
from app.shared.services.cache.semantic_cache import SemanticCacheService
from app.core.logging import get_logger

logger = get_logger(__name__)

MIN_CONFIDENCE = 0.8


async def warm_cache(session: AsyncSession) -> int:
    """Warm cache from golden dataset."""
    cache = SemanticCacheService()

    # Get high-quality findings
    stmt = (
        select(AgentFinding, Analysis)
        .join(Analysis, AgentFinding.analysis_id == Analysis.id)
        .where(AgentFinding.confidence_score >= MIN_CONFIDENCE)
    )

    result = await session.execute(stmt)
    findings = result.all()

    logger.info(f"Warming cache with {len(findings)} entries")

    warmed = 0
    for finding, analysis in findings:
        try:
            await cache.set(
                content=analysis.extracted_content or "",
                response=finding.findings,
                agent_type=finding.agent_type,
                content_type=analysis.content_type,
                quality_score=finding.confidence_score or 0.9,
            )
            warmed += 1
        except Exception as e:
            logger.warning(f"Failed to warm entry: {e}")

    logger.info(f"Warmed {warmed} cache entries")
    return warmed


async def main():
    async with async_session_factory() as session:
        count = await warm_cache(session)
        print(f"Warmed Redis cache with {count} entries")
        print(f"Stats: {SemanticCacheService().get_stats()}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 3 Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| L2 Redis hit rate | >35% | Redis stats |
| L3 Prompt cache hit rate | >80% | Claude API response |
| Combined cost reduction | >70% | Cost tracking |
| Latency improvement | >50% (cache hits) | Prometheus |
| Cache warmup coverage | 100% golden | Script output |

---

## Phase 4: Simplified Tree-of-Thoughts

**Duration:** 2-3 weeks | **Risk:** Low | **Dependencies:** Phase 0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: SIMPLIFIED TREE-OF-THOUGHTS                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GOAL: Improve conflict resolution quality through multi-perspective        │
│        analysis without the complexity of full BFS/DFS tree search          │
│                                                                              │
│  APPROACH:                                                                   │
│  - Use "three experts" prompt pattern (74% of full ToT benefit)             │
│  - Single LLM call instead of multiple tree traversals                      │
│  - Only trigger when agent confidence gap > 0.3                             │
│                                                                              │
│  FILES TO CREATE:                                                           │
│  ├─ tasks/aggregation/conflict_resolution/detector.py                       │
│  ├─ tasks/aggregation/conflict_resolution/simplified_tot.py                 │
│  └─ app/domains/analysis/schemas/conflict_resolution.py                     │
│                                                                              │
│  FILES TO MODIFY:                                                           │
│  └─ tasks/aggregation/synthesis_phased.py                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Conflict Detection

```python
# File: backend/app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/detector.py

"""Detect conflicts between agent findings."""

from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Conflict:
    """A detected conflict between agent findings."""

    conflict_id: str
    agent_a: str
    agent_a_position: str
    agent_a_confidence: float
    agent_b: str
    agent_b_position: str
    agent_b_confidence: float
    topic: str
    confidence_gap: float


def detect_conflicts(
    findings: list[dict],
    min_gap: float = 0.3,
) -> list[Conflict]:
    """Detect conflicts between agent findings.

    A conflict exists when:
    1. Two agents make recommendations on the same topic
    2. The recommendations are contradictory
    3. The confidence gap is significant (> min_gap)

    Args:
        findings: List of agent finding dictionaries
        min_gap: Minimum confidence gap to consider a conflict

    Returns:
        List of detected conflicts
    """
    conflicts = []

    # Extract recommendations from each agent
    recommendations = {}
    for finding in findings:
        agent_type = finding.get("agent_type", "unknown")
        agent_findings = finding.get("findings", {})
        confidence = finding.get("confidence_score", 0.5)

        # Extract key recommendations
        recs = agent_findings.get("recommendations", [])
        for rec in recs:
            topic = rec.get("topic", "general")
            position = rec.get("recommendation", "")

            if topic not in recommendations:
                recommendations[topic] = []

            recommendations[topic].append({
                "agent": agent_type,
                "position": position,
                "confidence": confidence,
            })

    # Find conflicts
    conflict_id = 0
    for topic, positions in recommendations.items():
        if len(positions) < 2:
            continue

        # Check all pairs
        for i, pos_a in enumerate(positions):
            for pos_b in positions[i + 1:]:
                # Check if positions are contradictory
                if _are_contradictory(pos_a["position"], pos_b["position"]):
                    gap = abs(pos_a["confidence"] - pos_b["confidence"])

                    if gap >= min_gap:
                        conflicts.append(Conflict(
                            conflict_id=f"conflict_{conflict_id}",
                            agent_a=pos_a["agent"],
                            agent_a_position=pos_a["position"],
                            agent_a_confidence=pos_a["confidence"],
                            agent_b=pos_b["agent"],
                            agent_b_position=pos_b["position"],
                            agent_b_confidence=pos_b["confidence"],
                            topic=topic,
                            confidence_gap=gap,
                        ))
                        conflict_id += 1

    logger.info(f"Detected {len(conflicts)} conflicts")
    return conflicts


def _are_contradictory(pos_a: str, pos_b: str) -> bool:
    """Check if two positions are contradictory.

    Simple heuristic: look for opposing keywords.
    """
    opposing_pairs = [
        ("use", "avoid"),
        ("recommended", "not recommended"),
        ("secure", "insecure"),
        ("fast", "slow"),
        ("yes", "no"),
        ("should", "should not"),
    ]

    pos_a_lower = pos_a.lower()
    pos_b_lower = pos_b.lower()

    for word_a, word_b in opposing_pairs:
        if (word_a in pos_a_lower and word_b in pos_b_lower) or \
           (word_b in pos_a_lower and word_a in pos_b_lower):
            return True

    return False
```

### 4.2 Simplified ToT Resolver

```python
# File: backend/app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/simplified_tot.py

"""Simplified Tree-of-Thoughts conflict resolution."""

from langchain_core.prompts import ChatPromptTemplate

from app.core.model_factory import get_chat_model
from app.core.logging import get_logger
from app.domains.analysis.schemas.conflict_resolution import ConflictResolution
from .detector import Conflict

logger = get_logger(__name__)


SIMPLIFIED_TOT_PROMPT = """You are resolving a conflict between two expert analysts.

## The Conflict

**Topic:** {topic}

**Position A ({agent_a}, confidence {confidence_a:.0%}):**
{position_a}

**Position B ({agent_b}, confidence {confidence_b:.0%}):**
{position_b}

## Your Task

Imagine three expert engineers analyzing this conflict:

**Expert 1 (Technical Depth):**
Focus on technical correctness, performance implications, and best practices.
What does the technical evidence support?

**Expert 2 (Practical Implementation):**
Focus on real-world usability, maintenance burden, and developer experience.
What's most practical for a development team?

**Expert 3 (Strategic Context):**
Consider the specific project context, timeline, and constraints.
What makes sense given the broader picture?

After each expert shares their perspective, synthesize a consensus position.
If true consensus isn't possible, document the trade-offs clearly.

## Resolution Format

Provide:
1. The resolved recommendation
2. Clear reasoning that addresses both original positions
3. A confidence score (0.0-1.0) for the resolution
4. Any caveats or conditions where the minority position might be preferred
"""


async def resolve_conflict(conflict: Conflict) -> ConflictResolution:
    """Resolve a conflict using simplified ToT pattern.

    Uses "three experts" prompt to get multi-perspective analysis
    without the overhead of full tree search.

    Args:
        conflict: The conflict to resolve

    Returns:
        ConflictResolution with synthesized recommendation
    """
    model = get_chat_model()
    structured_model = model.with_structured_output(ConflictResolution)

    prompt = ChatPromptTemplate.from_template(SIMPLIFIED_TOT_PROMPT)
    chain = prompt | structured_model

    result = await chain.ainvoke({
        "topic": conflict.topic,
        "agent_a": conflict.agent_a,
        "confidence_a": conflict.agent_a_confidence,
        "position_a": conflict.agent_a_position,
        "agent_b": conflict.agent_b,
        "confidence_b": conflict.agent_b_confidence,
        "position_b": conflict.agent_b_position,
    })

    logger.info(
        "conflict_resolved",
        conflict_id=conflict.conflict_id,
        resolution_confidence=result.confidence,
    )

    return result


async def resolve_all_conflicts(conflicts: list[Conflict]) -> list[ConflictResolution]:
    """Resolve all conflicts."""
    resolutions = []

    for conflict in conflicts:
        resolution = await resolve_conflict(conflict)
        resolutions.append(resolution)

    return resolutions
```

---

## Phase 5: ReAct Enhancement

**Duration:** 1-2 weeks | **Risk:** Low | **Dependencies:** Phase 0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 5: REACT ENHANCEMENT                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GOAL: Improve observability of tool-using agents through                   │
│        explicit reasoning traces (NOT changing execution pattern)           │
│                                                                              │
│  APPROACH:                                                                   │
│  - Keep native function calling (already implemented)                       │
│  - Add reasoning trace prompts for observability                            │
│  - Integrate traces with LangSmith for debugging                            │
│                                                                              │
│  NOTE: Current implementation already uses provider native function         │
│        calling which is 40% faster than custom ReAct parsing.               │
│        This phase only adds observability, not execution changes.           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Implementation details in `docs/advanced-llm-techniques.md` Section 5.

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION DEPENDENCIES                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              Phase 0
                         (Infrastructure)
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
        Phase 1            Phase 2            Phase 3
      (Few-Shot)         (CoT Super)      (Double Cache)
            │                  │                  │
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                           Phase 4
                       (Simplified ToT)
                               │
                               ▼
                           Phase 5
                       (ReAct Enhance)


PARALLEL EXECUTION POSSIBLE:
- Phase 1, 2, 3 can run in parallel after Phase 0
- Phase 4 requires some findings to test conflicts
- Phase 5 is independent, can run anytime after Phase 0

RECOMMENDED SEQUENCE:
Week 1:     Phase 0 (Infrastructure)
Week 2-4:   Phase 1 (Few-Shot) || Phase 3 (Caching) in parallel
Week 5-8:   Phase 2 (CoT Supervisor)
Week 9-11:  Phase 4 (Simplified ToT)
Week 12-14: Phase 5 (ReAct Enhancement)
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Redis connection issues | Medium | High | Graceful fallback to L3/L4 caching |
| CoT increases latency too much | Low | Medium | Feature flag to disable, content threshold |
| Few-shot examples reduce diversity | Low | Medium | Diversity filtering in selector |
| Cache poisoning (bad responses) | Low | High | Quality score filtering, TTL expiration |
| A/B test insufficient sample size | Medium | Medium | Extend test duration, 20%+ traffic |

---

## Rollback Procedures

### Immediate Rollback (Any Phase)

```bash
# Disable all techniques instantly
export TECHNIQUE_ENABLE_FEW_SHOT=false
export TECHNIQUE_ENABLE_COT_SUPERVISOR=false
export TECHNIQUE_ENABLE_REDIS_CACHE=false
export TECHNIQUE_ENABLE_PROMPT_CACHING=false
export TECHNIQUE_ENABLE_TOT_RESOLVER=false
export TECHNIQUE_ENABLE_REACT_TRACING=false

# Restart backend
docker compose restart backend
```

### Redis Rollback

```bash
# Clear all cache entries
docker exec skillforge-redis redis-cli FLUSHALL

# Or remove Redis entirely
docker compose stop redis
docker compose rm redis

# Set flag to disable
export TECHNIQUE_ENABLE_REDIS_CACHE=false
```

### Database Rollback (Phase 1)

```bash
# Rollback migration
cd backend
poetry run alembic downgrade -1

# This drops agent_examples table
```

---

## Success Metrics & Monitoring

### Dashboard Metrics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KEY PERFORMANCE INDICATORS                          │
└─────────────────────────────────────────────────────────────────────────────┘

QUALITY METRICS (LangSmith):
┌─────────────────────────────────────────────────────────────────┐
│  • Agent output quality score (human feedback)                   │
│  • Supervisor selection accuracy                                 │
│  • Conflict resolution satisfaction                              │
│  • Synthesis coherence score                                     │
└─────────────────────────────────────────────────────────────────┘

PERFORMANCE METRICS (Prometheus/Grafana):
┌─────────────────────────────────────────────────────────────────┐
│  • End-to-end analysis latency (P50, P95, P99)                  │
│  • Cache hit rates (L1, L2, L3)                                 │
│  • Token usage per analysis                                      │
│  • Error rate by component                                       │
└─────────────────────────────────────────────────────────────────┘

COST METRICS (Custom):
┌─────────────────────────────────────────────────────────────────┐
│  • Estimated USD per analysis                                    │
│  • Token savings from caching                                    │
│  • Cost trend (daily/weekly)                                     │
└─────────────────────────────────────────────────────────────────┘

A/B TEST METRICS:
┌─────────────────────────────────────────────────────────────────┐
│  • Treatment vs Control quality comparison                       │
│  • Statistical significance (p-value)                            │
│  • Sample size per variant                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Alerting Rules

```yaml
# Example Prometheus alerting rules

groups:
  - name: llm_techniques
    rules:
      - alert: CacheHitRateLow
        expr: redis_cache_hit_rate < 0.2
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Redis cache hit rate below 20%"

      - alert: SupervisorLatencyHigh
        expr: supervisor_latency_p95 > 5000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Supervisor latency P95 > 5s"

      - alert: TechniqueErrorRateHigh
        expr: technique_error_rate > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Technique error rate > 5%"
```

---

## Appendix: File Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE FILE CHECKLIST                             │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 0 - Infrastructure:
[ ] app/core/feature_flags.py
[ ] app/shared/services/metrics/technique_metrics.py
[ ] Directory structure creation

PHASE 1 - Few-Shot:
[ ] alembic/versions/xxx_add_agent_examples.py
[ ] app/models/agent_example.py
[ ] app/db/repositories/agent_examples.py
[ ] app/domains/analysis/workflows/agents/techniques/__init__.py
[ ] app/domains/analysis/workflows/agents/techniques/few_shot.py
[ ] app/domains/analysis/workflows/agents/prompt_builders.py (modify)
[ ] scripts/seed_few_shot_examples.py
[ ] tests/unit/workflows/agents/techniques/test_few_shot.py

PHASE 2 - CoT Supervisor:
[ ] app/domains/analysis/schemas/supervisor/reasoning_log.py
[ ] app/domains/analysis/workflows/nodes/supervisor/__init__.py
[ ] app/domains/analysis/workflows/nodes/supervisor/cot_reasoning.py
[ ] app/domains/analysis/workflows/nodes/supervisor/decision_validator.py
[ ] app/domains/analysis/workflows/nodes/supervisor.py (modify)
[ ] tests/unit/workflows/nodes/supervisor/test_cot_reasoning.py

PHASE 3 - Caching:
[ ] docker-compose.yml (modify - add Redis)
[ ] app/shared/services/cache/__init__.py
[ ] app/shared/services/cache/semantic_cache.py
[ ] app/shared/services/cache/prompt_cache.py
[ ] app/shared/services/cache/cache_manager.py
[ ] app/core/model_factory.py (modify - add caching)
[ ] scripts/warm_redis_cache.py
[ ] tests/unit/services/cache/test_semantic_cache.py

PHASE 4 - ToT:
[ ] app/domains/analysis/schemas/conflict_resolution.py
[ ] app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/__init__.py
[ ] app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/detector.py
[ ] app/domains/analysis/workflows/tasks/aggregation/conflict_resolution/simplified_tot.py
[ ] app/domains/analysis/workflows/tasks/aggregation/synthesis_phased.py (modify)
[ ] tests/unit/workflows/tasks/aggregation/test_conflict_resolution.py

PHASE 5 - ReAct:
[ ] app/domains/analysis/workflows/agents/techniques/react_tracing.py
[ ] app/domains/analysis/workflows/agents/base.py (modify)
[ ] tests/unit/workflows/agents/techniques/test_react_tracing.py
```

---

*Document maintained as part of SkillForge architecture documentation.*
*Last updated: 2025-12-16*
