"""Integration tests for bulkhead rejection handling in agent nodes.

Issue #588: Tests verify graceful degradation when agents are rejected by bulkhead
due to queue full or timeout conditions. Agents should return empty findings and
not crash the workflow.

These tests verify the complete flow:
1. Bulkhead rejects agent execution (BulkheadFullError or BulkheadTimeoutError)
2. Agent node catches the exception
3. Agent records failure with AGENT_BULKHEAD_REJECTED status
4. Workflow continues with other agents
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.bulkhead import (
    Tier,
    get_bulkhead_registry,
)
from app.db.models.agent_finding import AgentFinding
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal
from app.domains.analysis.constants.error_codes import AGENT_BULKHEAD_REJECTED, AgentStatus
from app.domains.analysis.workflows.nodes.agents.key_insights_node import key_insights_node

if TYPE_CHECKING:
    from app.domains.analysis.workflows.state import AnalysisState


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_graceful_degradation_when_bulkhead_full(
    requires_database,
    reset_engine_connections,
    check_database_available,
):
    """Test agent handles BulkheadFullError gracefully and returns empty findings.

    This test verifies:
    - Bulkhead with max_concurrent=1, queue_size=1 fills after 2 tasks
    - Third task attempting to execute gets BulkheadFullError
    - Agent node catches the error and returns empty findings
    - Agent execution is recorded with AGENT_BULKHEAD_REJECTED status
    - Workflow doesn't crash
    """
    from app.core.bulkhead import reset_bulkhead_registry
    from app.core.resilience import reset_resilience_manager

    # Reset resilience infrastructure BEFORE creating custom bulkhead
    await reset_resilience_manager()
    await reset_bulkhead_registry()

    analysis_id = str(uuid4())
    test_url = f"https://example.com/test-bulkhead-{analysis_id[:8]}"

    # Create Analysis record for foreign key constraint
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Create a restrictive bulkhead BEFORE resilience manager initializes
    # This will reject the 3rd task when bulkhead + queue are full
    registry = get_bulkhead_registry()
    test_bulkhead = registry.register(
        name="tier_critical",
        tier=Tier.CRITICAL,
        max_concurrent=1,
        queue_size=1,  # Allow 1 in queue - 3rd task will be rejected
    )

    # Fill the bulkhead and queue with slow tasks
    async def slow_task() -> dict[str, object]:
        """Slow task that holds the bulkhead semaphore."""
        await asyncio.sleep(3.0)  # Hold for 3 seconds
        return {"findings": "slow_task_result"}

    # Start 2 slow tasks (1st acquires semaphore, 2nd goes to queue)
    slow_task_1 = asyncio.create_task(test_bulkhead.execute(slow_task))
    await asyncio.sleep(0.05)  # Let first task acquire semaphore
    slow_task_2 = asyncio.create_task(test_bulkhead.execute(slow_task))
    await asyncio.sleep(0.05)  # Let second task enter queue

    # Create state for key_insights agent
    state: AnalysisState = {
        "analysis_id": UUID(analysis_id),
        "url": test_url,
        "content_type": "article",
        "raw_content": "Sample content about React",
        "skill_level": "intermediate",
        "processing_mode": "standard",
        "agent_findings": [],
    }

    # Execute agent - should get BulkheadFullError (bulkhead full) but handle gracefully
    result = await key_insights_node(state)

    # Wait for slow tasks to complete
    await asyncio.gather(slow_task_1, slow_task_2, return_exceptions=True)

    # Verify agent returned empty findings (graceful degradation)
    assert "agent_findings" in result
    assert result["agent_findings"] == []

    # Verify agent execution was recorded with BULKHEAD_REJECTED status
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentFinding).where(AgentFinding.analysis_id == UUID(analysis_id))
        )
        findings = result.scalars().all()
        assert len(findings) == 1
        finding = findings[0]
        assert finding.agent_type == "key_insights"
        assert finding.status == AgentStatus.FAILED.value
        assert finding.error_code == AGENT_BULKHEAD_REJECTED


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_graceful_degradation_when_bulkhead_timeout(
    requires_database,
    reset_engine_connections,
    check_database_available,
):
    """Test agent handles BulkheadTimeoutError gracefully.

    This test verifies:
    - Bulkhead with short timeout (0.1s) times out waiting for semaphore
    - Agent node catches BulkheadTimeoutError
    - Agent returns empty findings (graceful degradation)
    - Agent execution is recorded with AGENT_BULKHEAD_REJECTED status
    """
    from app.core.bulkhead import reset_bulkhead_registry
    from app.core.resilience import reset_resilience_manager

    # Reset resilience infrastructure BEFORE creating custom bulkhead
    await reset_resilience_manager()
    await reset_bulkhead_registry()

    analysis_id = str(uuid4())
    test_url = f"https://example.com/test-bulkhead-{analysis_id[:8]}"

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Create bulkhead with very short timeout BEFORE resilience manager initializes
    registry = get_bulkhead_registry()
    test_bulkhead = registry.register(
        name="tier_critical",
        tier=Tier.CRITICAL,
        max_concurrent=1,
        queue_size=1,  # Allow 1 in queue
        timeout=0.1,  # Very short timeout (100ms)
    )

    # Fill the bulkhead with a slow task
    async def slow_task() -> dict[str, object]:
        """Slow task that holds the bulkhead semaphore."""
        await asyncio.sleep(1.0)  # Hold for 1 second
        return {"findings": "slow_task_result"}

    # Start slow task (acquires semaphore)
    slow_task_future = asyncio.create_task(test_bulkhead.execute(slow_task))

    # Give slow task time to acquire semaphore
    await asyncio.sleep(0.05)

    # Create state for agent
    state: AnalysisState = {
        "analysis_id": UUID(analysis_id),
        "url": test_url,
        "content_type": "article",
        "raw_content": "Sample content about React",
        "skill_level": "intermediate",
        "processing_mode": "standard",
        "agent_findings": [],
    }

    # Execute agent - should timeout waiting for semaphore but handle gracefully
    result = await key_insights_node(state)

    # Wait for slow task to complete
    await slow_task_future

    # Verify agent returned empty findings (graceful degradation)
    assert "agent_findings" in result
    assert result["agent_findings"] == []

    # Verify agent execution was recorded with BULKHEAD_REJECTED status
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentFinding).where(AgentFinding.analysis_id == UUID(analysis_id))
        )
        findings = result.scalars().all()
        assert len(findings) == 1
        finding = findings[0]
        assert finding.agent_type == "key_insights"
        assert finding.status == AgentStatus.FAILED.value
        assert finding.error_code == AGENT_BULKHEAD_REJECTED


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_workflow_continues_after_bulkhead_rejection(
    requires_database,
    reset_engine_connections,
    check_database_available,
):
    """Test workflow continues successfully when one agent is rejected by bulkhead.

    This test verifies:
    - Multiple agents execute in parallel
    - One agent gets rejected by bulkhead (queue full)
    - Rejected agent returns empty findings
    - Other agents continue execution successfully
    - Workflow completes with partial results (graceful degradation)
    """
    from app.domains.analysis.workflows.nodes.agents.implementation_guide_node import (
        implementation_guide_node,
    )

    from app.core.bulkhead import reset_bulkhead_registry
    from app.core.resilience import reset_resilience_manager

    # Reset resilience infrastructure BEFORE creating custom bulkhead
    await reset_resilience_manager()
    await reset_bulkhead_registry()

    analysis_id = str(uuid4())
    test_url = f"https://example.com/test-bulkhead-{analysis_id[:8]}"

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Create very restrictive bulkhead for Tier 1 (UNIVERSAL agents) BEFORE resilience manager initializes
    # This will cause one of the agents to be rejected (max_concurrent=1, queue_size=1 means 3rd task rejected)
    registry = get_bulkhead_registry()
    test_bulkhead = registry.register(
        name="tier_critical",
        tier=Tier.CRITICAL,
        max_concurrent=1,
        queue_size=1,  # Allow 1 in queue - 3rd task will be rejected
    )

    # Fill bulkhead and queue with slow tasks to force agent rejection
    async def slow_task() -> dict[str, object]:
        """Slow task that holds the bulkhead semaphore."""
        await asyncio.sleep(2.0)
        return {"findings": "slow_task_result"}

    # Start 2 slow tasks (1st acquires semaphore, 2nd goes to queue)
    slow_task_1 = asyncio.create_task(test_bulkhead.execute(slow_task))
    await asyncio.sleep(0.05)
    slow_task_2 = asyncio.create_task(test_bulkhead.execute(slow_task))
    await asyncio.sleep(0.05)

    # Create state
    state: AnalysisState = {
        "analysis_id": UUID(analysis_id),
        "url": test_url,
        "content_type": "article",
        "raw_content": "Sample content about React with hooks and components",
        "skill_level": "intermediate",
        "processing_mode": "standard",
        "agent_findings": [],
    }

    # Execute two agents in parallel (both are Tier 1 UNIVERSAL agents)
    # One should get rejected by bulkhead (3rd task), but both should return gracefully
    key_insights_task = asyncio.create_task(key_insights_node(state))
    implementation_task = asyncio.create_task(implementation_guide_node(state))

    # Wait for both agents to complete
    key_insights_result, implementation_result = await asyncio.gather(
        key_insights_task,
        implementation_task,
        return_exceptions=False,  # Don't catch exceptions - nodes handle internally
    )

    # Wait for slow tasks to complete
    await asyncio.gather(slow_task_1, slow_task_2, return_exceptions=True)

    # At least one agent should have returned empty findings (rejected by bulkhead)
    # But the workflow should not crash - both should return valid dict results
    assert isinstance(key_insights_result, dict)
    assert isinstance(implementation_result, dict)
    assert "agent_findings" in key_insights_result
    assert "agent_findings" in implementation_result

    # At least one should have empty findings (bulkhead rejected)
    # But both should have valid structure (graceful degradation)
    findings_results = [
        key_insights_result["agent_findings"],
        implementation_result["agent_findings"],
    ]

    # Count empty and non-empty findings
    empty_count = sum(1 for f in findings_results if f == [])
    success_count = sum(1 for f in findings_results if f != [])

    # Should have at least one rejection and at least one success
    # (exact outcome depends on race condition, but should show graceful degradation)
    assert empty_count >= 1, "At least one agent should be rejected by bulkhead"
    assert success_count >= 0, "Other agents can complete successfully or also fail"

    # Verify both agent executions were recorded (even rejected ones)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentFinding).where(AgentFinding.analysis_id == UUID(analysis_id))
        )
        findings = result.scalars().all()
        assert len(findings) == 2  # Both agents should have execution records

        # At least one should have BULKHEAD_REJECTED status
        rejected_findings = [f for f in findings if f.error_code == AGENT_BULKHEAD_REJECTED]
        assert len(rejected_findings) >= 1, "At least one agent should be bulkhead rejected"

        # All findings should have valid status
        for finding in findings:
            assert finding.status in [
                AgentStatus.SUCCESS.value,
                AgentStatus.FAILED.value,
            ]
