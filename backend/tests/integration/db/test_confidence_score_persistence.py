"""Integration tests for confidence_score database persistence."""

import uuid

import pytest
from sqlalchemy import select

from app.db.models.agent_finding import AgentFinding
from app.db.models.analysis import Analysis


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_score_saved_correctly(requires_database, db_session):
    """Test that confidence_score is saved correctly with float precision preserved."""
    analysis_id = uuid.uuid4()
    confidence_value = 0.123456

    # Create analysis
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create finding with confidence_score
    finding = AgentFinding(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings={"primary_tech": "React"},
        confidence_score=confidence_value,
        processing_time_ms=1000,
    )
    db_session.add(finding)
    await db_session.commit()
    await db_session.refresh(finding)

    # Query and verify
    result = await db_session.execute(select(AgentFinding).where(AgentFinding.id == finding.id))
    retrieved_finding = result.scalar_one_or_none()

    assert retrieved_finding is not None
    assert retrieved_finding.confidence_score == confidence_value
    assert isinstance(retrieved_finding.confidence_score, float)
    # Verify precision is preserved
    assert abs(retrieved_finding.confidence_score - confidence_value) < 0.000001


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_score_queryable(requires_database, db_session):
    """Test that confidence_score can be queried and filtered."""
    analysis_id = uuid.uuid4()

    # Create analysis
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create findings with different confidence scores
    finding1 = AgentFinding(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings={"primary_tech": "React"},
        confidence_score=0.8,
    )
    finding2 = AgentFinding(
        analysis_id=analysis_id,
        agent_type="implementation_planner",
        findings={"steps": []},
        confidence_score=0.6,
    )
    db_session.add(finding1)
    db_session.add(finding2)
    await db_session.commit()

    # Query by confidence_score range
    from sqlalchemy import and_

    result = await db_session.execute(
        select(AgentFinding).where(
            and_(
                AgentFinding.analysis_id == analysis_id,
                AgentFinding.confidence_score >= 0.7,
            )
        )
    )
    high_confidence_findings = result.scalars().all()

    assert len(high_confidence_findings) == 1
    assert high_confidence_findings[0].confidence_score == 0.8


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_score_aggregation(requires_database, db_session):
    """Test that confidence_score can be used in aggregations (AVG, MIN, MAX)."""
    analysis_id = uuid.uuid4()

    # Create analysis
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create findings with different confidence scores
    scores = [0.5, 0.7, 0.9, 0.6, 0.8]
    for i, score in enumerate(scores):
        finding = AgentFinding(
            analysis_id=analysis_id,
            agent_type=f"agent_{i}",
            findings={"test": "data"},
            confidence_score=score,
        )
        db_session.add(finding)
    await db_session.commit()

    # Test aggregations
    from sqlalchemy import func

    # AVG
    result_avg = await db_session.execute(
        select(func.avg(AgentFinding.confidence_score)).where(
            AgentFinding.analysis_id == analysis_id
        )
    )
    avg_score = result_avg.scalar()
    assert avg_score is not None
    assert 0.0 <= avg_score <= 1.0
    assert abs(avg_score - 0.7) < 0.01  # Should be close to 0.7

    # MIN
    result_min = await db_session.execute(
        select(func.min(AgentFinding.confidence_score)).where(
            AgentFinding.analysis_id == analysis_id
        )
    )
    min_score = result_min.scalar()
    assert min_score == 0.5

    # MAX
    result_max = await db_session.execute(
        select(func.max(AgentFinding.confidence_score)).where(
            AgentFinding.analysis_id == analysis_id
        )
    )
    max_score = result_max.scalar()
    assert max_score == 0.9


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_score_indexing(requires_database, db_session):
    """Test that queries on confidence_score are performant (indexed)."""
    analysis_id = uuid.uuid4()

    # Create analysis
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create finding
    finding = AgentFinding(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings={"primary_tech": "React"},
        confidence_score=0.85,
    )
    db_session.add(finding)
    await db_session.commit()

    # Query by confidence_score - should be fast (indexed)
    import time

    start_time = time.time()
    result = await db_session.execute(
        select(AgentFinding).where(AgentFinding.confidence_score >= 0.8)
    )
    findings_list = result.scalars().all()
    query_time = time.time() - start_time

    assert len(findings_list) >= 1
    # Query should complete quickly (< 100ms for indexed column)
    assert query_time < 0.1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_score_null_handling(requires_database, db_session):
    """Test that NULL confidence_score values don't break queries (backward compatibility)."""
    analysis_id = uuid.uuid4()

    # Create analysis
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create finding with NULL confidence_score (old record)
    finding = AgentFinding(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings={"primary_tech": "React"},
        confidence_score=None,  # NULL for backward compatibility
    )
    db_session.add(finding)
    await db_session.commit()

    # Query should work with NULL values
    result = await db_session.execute(
        select(AgentFinding).where(AgentFinding.analysis_id == analysis_id)
    )
    retrieved_finding = result.scalar_one_or_none()

    assert retrieved_finding is not None
    assert retrieved_finding.confidence_score is None

    # Aggregations should handle NULL (exclude from calculations)
    from sqlalchemy import func

    result_avg = await db_session.execute(
        select(func.avg(AgentFinding.confidence_score)).where(
            AgentFinding.analysis_id == analysis_id
        )
    )
    # AVG of NULL should return NULL, not error
    avg_score = result_avg.scalar()
    # NULL is acceptable - aggregations handle it gracefully
    assert avg_score is None or 0.0 <= avg_score <= 1.0
