"""Scale and concurrency tests for Sprint 11 Context Engineering.

Tests verify that context engineering features handle:
- Concurrent memory access from multiple agents
- Large state handling (>100KB)
- Parallel routing with memory injection
- High throughput session compaction
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.services.context.compaction import (
    CompactionConfig,
    CompiledContext,
    SessionCompactor,
)
from app.domains.analysis.workflows.nodes.agent_router import route_to_agents
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.aggregate_findings import (
    _extract_finding_content,
    _store_findings_as_memories,
)
from app.shared.workflows.context_scope import build_scoped_context


class TestConcurrentMemoryAccess:
    """Tests for concurrent memory operations."""

    @pytest.mark.asyncio
    async def test_concurrent_routing_with_memory_injection(self) -> None:
        """Test that multiple analyses can route concurrently with memory injection."""
        states = [
            {
                "analysis_id": str(uuid4()),
                "url": f"https://example.com/article-{i}",
                "content_type": "article",
                "content_ref": {"uri": f"analysis://test/content-{i}", "summary": f"Article {i}"},
                "raw_content": f"Test content {i}",
                "supervisor_decision": {
                    "agents": ["security_auditor", "tech_comparator"],
                    "priority": [0.9, 0.8],
                    "reasoning": f"Analysis {i}",
                    "confidence": 0.85,
                },
                "skill_level": "intermediate",
            }
            for i in range(10)
        ]

        # Mock memory fetch to return unique data per analysis
        async def mock_memory_fetch(agent_type: str, content_summary: str) -> str:
            await asyncio.sleep(0.01)  # Simulate async DB access
            return f"Memory for {agent_type}: {content_summary[:20]}"

        with patch(
            "app.workflows.nodes.agent_router._fetch_agent_memory",
            side_effect=mock_memory_fetch,
        ):
            # Run all routes concurrently
            results = await asyncio.gather(*[route_to_agents(state) for state in states])

            # All should succeed
            assert len(results) == 10
            for result in results:
                assert len(result) == 2  # 2 agents each

    @pytest.mark.asyncio
    async def test_memory_storage_under_concurrent_load(self) -> None:
        """Test storing findings from multiple analyses concurrently."""
        analyses = [
            {
                "analysis_id": str(uuid4()),
                "findings": [
                    {
                        "agent_type": "security_auditor",
                        "findings": {"recommendation": f"Security fix {i}"},
                        "confidence_score": 0.9,
                    },
                    {
                        "agent_type": "tech_comparator",
                        "findings": {"primary_tech": f"Tech {i}"},
                        "confidence_score": 0.85,
                    },
                ],
            }
            for i in range(20)
        ]

        stored_counts = []

        with (
            patch("app.workflows.tasks.aggregate_findings.get_session_factory") as mock_factory,
            patch(
                "app.workflows.tasks.aggregate_findings.AgentMemoryService"
            ) as mock_service_class,
        ):
            # Setup mocks
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_factory.return_value = MagicMock(return_value=mock_session)

            mock_service = AsyncMock()
            mock_service.store.return_value = MagicMock(id=uuid4())
            mock_service_class.return_value = mock_service

            async def store_with_delay(analysis_id: str, findings: list) -> int:
                await asyncio.sleep(0.01)  # Simulate DB latency
                return await _store_findings_as_memories(analysis_id, findings)

            # Run concurrently
            stored_counts = await asyncio.gather(
                *[store_with_delay(a["analysis_id"], a["findings"]) for a in analyses]
            )

        # All should succeed
        assert len(stored_counts) == 20
        assert all(count == 2 for count in stored_counts)  # 2 findings each


class TestLargeStateHandling:
    """Tests for handling large state objects."""

    def test_scoping_with_100kb_state(self) -> None:
        """Test that scoping handles 100KB+ state efficiently."""
        # Create a very large state
        large_state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "raw_content": "X" * 100000,  # 100KB
            "content_ref": {
                "uri": "analysis://test/content",
                "summary": "Large article",
                "size_bytes": 100000,
            },
            "content_embedding": [0.1] * 1536,  # ~12KB
            "extraction_metadata": {
                "details": "Y" * 10000,  # 10KB metadata
            },
            "supervisor_decision": {"agents": ["security_auditor"]},
            "skill_level": "advanced",
            "agent_findings": [{"agent_type": "prior", "findings": {"data": "Z" * 5000}}],
        }

        # Verify state is large
        original_size = len(str(large_state))
        assert original_size > 100000

        # Test scoping for all agents
        for agent_type in ["security_auditor", "tech_comparator", "implementation_planner"]:
            scoped = build_scoped_context(large_state, agent_type)

            scoped_size = len(str(scoped))
            reduction = ((original_size - scoped_size) / original_size) * 100

            # Should achieve at least 99% reduction for large states
            assert reduction > 99, f"Agent {agent_type} only achieved {reduction:.1f}% reduction"

            # Scoped state should be < 1KB typically
            assert scoped_size < 2000, f"Scoped state too large: {scoped_size} bytes"

    def test_content_extraction_with_large_findings(self) -> None:
        """Test content extraction truncates large findings properly."""
        large_finding = {
            "recommendation": "X" * 5000,  # 5KB recommendation
            "security_risks": [
                {"risk_type": f"risk_{i}", "description": "Y" * 500}
                for i in range(20)  # 20 risks
            ],
        }

        content = _extract_finding_content("security_auditor", large_finding)

        # Should be truncated to 2000 chars
        assert len(content) <= 2000


class TestSessionCompactionScale:
    """Scale tests for session compaction."""

    @pytest.mark.asyncio
    async def test_concurrent_session_compaction(self) -> None:
        """Test multiple sessions can be compacted concurrently."""
        compactor = SessionCompactor(CompactionConfig(max_turns_full=3, summarize_after=5))

        # Create 10 histories that need compaction
        histories = [
            [{"role": "user", "content": f"Session {i} Message {j}"} for j in range(8)]
            for i in range(10)
        ]

        with patch.object(compactor, "_summarize_turns", new_callable=AsyncMock) as mock_summarize:
            # Each call returns unique summary
            mock_summarize.side_effect = [f"Summary of session {i}" for i in range(10)]

            # Compact all sessions concurrently
            results = await asyncio.gather(*[compactor.compact(h) for h in histories])

            # All should succeed with compaction
            assert len(results) == 10
            for result in results:
                assert result.compression_ratio < 1.0
                assert result.compiled_count < result.original_count

    @pytest.mark.asyncio
    async def test_large_conversation_history(self) -> None:
        """Test compaction with very large conversation history."""
        compactor = SessionCompactor(CompactionConfig(max_turns_full=5, summarize_after=10))

        # 50-turn conversation
        large_history = [
            {"role": role, "content": f"Turn {i // 2}: " + "X" * 100}
            for i, role in enumerate(["user", "assistant"] * 25)
        ]

        with patch.object(compactor, "_summarize_turns", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = "Summary of extensive conversation about various topics."

            result = await compactor.compact(large_history)

            # Should have compacted significantly
            assert result.original_count == 50
            assert result.compiled_count <= 10  # At most 5 full + some prefix
            assert result.compression_ratio < 0.25


class TestRoutingScale:
    """Scale tests for agent routing."""

    @pytest.mark.asyncio
    async def test_route_all_8_agents_with_memory(self) -> None:
        """Test routing to all 8 agents with memory injection."""
        state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "content_ref": {"uri": "analysis://test/content", "summary": "Comprehensive article"},
            "raw_content": "Test content",
            "supervisor_decision": {
                "agents": [
                    "tech_comparator",
                    "security_auditor",
                    "implementation_planner",
                    "performance_analyst",
                    "code_quality_critic",
                    "trend_validator",
                    "dependency_mapper",
                    "integration_feasibility",
                ],
                "priority": [0.9] * 8,
                "reasoning": "Full analysis",
                "confidence": 0.95,
            },
            "skill_level": "advanced",
        }

        with patch(
            "app.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = "Prior context memory"

            sends = await route_to_agents(state)

            # Should create 8 sends
            assert len(sends) == 8

            # Verify agents that should have memory (inject_memory=True)
            agents_with_memory = [
                "security_auditor",
                "tech_comparator",
                "implementation_planner",
                "integration_feasibility",
            ]

            for send in sends:
                if send.node in agents_with_memory:
                    # These agents should have prior_memory
                    assert "prior_memory" in send.arg, f"{send.node} missing prior_memory"
                else:
                    # Others should not
                    assert "prior_memory" not in send.arg, (
                        f"{send.node} has unexpected prior_memory"
                    )

    @pytest.mark.asyncio
    async def test_routing_throughput(self) -> None:
        """Test routing throughput with many analyses."""
        import time

        states = [
            {
                "analysis_id": str(uuid4()),
                "url": f"https://example.com/{i}",
                "content_type": "article",
                "content_ref": {"uri": f"analysis://test/{i}", "summary": f"Article {i}"},
                "raw_content": "Test",
                "supervisor_decision": {
                    "agents": ["security_auditor", "tech_comparator"],
                    "priority": [0.9, 0.8],
                    "reasoning": "Test",
                    "confidence": 0.85,
                },
                "skill_level": "intermediate",
            }
            for i in range(100)
        ]

        # Mock memory to be fast
        with patch(
            "app.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = ""

            start = time.time()
            results = await asyncio.gather(*[route_to_agents(s) for s in states])
            elapsed = time.time() - start

            # All should succeed
            assert len(results) == 100
            # Should complete in reasonable time (< 5s for 100 routes)
            assert elapsed < 5.0, f"Routing took too long: {elapsed:.2f}s"


class TestCompilerScale:
    """Scale tests for context compilation."""

    @pytest.mark.asyncio
    async def test_compile_with_large_session_history(self) -> None:
        """Test compilation with large session history."""
        from app.shared.workflows.context_compiler import create_workflow_compiler

        compiler = create_workflow_compiler("tutor")

        # Large history (100 messages)
        large_history = [
            {"role": role, "content": f"Message {i}: " + "Y" * 50}
            for i, role in enumerate(["user", "assistant"] * 50)
        ]

        with patch.object(compiler.compactor, "compact", new_callable=AsyncMock) as mock_compact:
            mock_compact.return_value = CompiledContext(
                prefix=[{"role": "system", "content": "Summary of 95 messages"}],
                messages=large_history[-5:],
                original_count=100,
                compiled_count=6,
                summary="Summary",
            )

            messages = await compiler.compile_for_invocation(
                session_history=large_history,
                current_input="New question",
            )

            # Should have compacted output
            assert len(messages) < 20  # Much smaller than 100

    @pytest.mark.asyncio
    async def test_multiple_compilers_concurrent(self) -> None:
        """Test multiple compilers operating concurrently."""
        from app.shared.workflows.context_compiler import create_workflow_compiler

        # Create different compilers
        tutor_compiler = create_workflow_compiler("tutor")
        analysis_compiler = create_workflow_compiler("analysis")

        histories = [
            [{"role": "user", "content": f"Message {i}"} for i in range(5)] for _ in range(10)
        ]

        with (
            patch.object(tutor_compiler.compactor, "compact", new_callable=AsyncMock) as mock_tutor,
            patch.object(
                analysis_compiler.compactor, "compact", new_callable=AsyncMock
            ) as mock_analysis,
        ):
            mock_tutor.return_value = CompiledContext(
                prefix=[], messages=histories[0], original_count=5, compiled_count=5, summary=None
            )
            mock_analysis.return_value = CompiledContext(
                prefix=[], messages=histories[0], original_count=5, compiled_count=5, summary=None
            )

            # Run mixed compilations
            tasks = []
            for i, h in enumerate(histories):
                compiler = tutor_compiler if i % 2 == 0 else analysis_compiler
                tasks.append(compiler.compile_for_invocation(session_history=h))

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 10


class TestScopingPerformance:
    """Performance tests for context scoping."""

    def test_scoping_is_fast_for_large_states(self) -> None:
        """Test that scoping completes quickly even for large states."""
        import time

        # Create large state
        large_state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "raw_content": "X" * 100000,
            "content_ref": {"uri": "test", "summary": "test"},
            "content_embedding": [0.1] * 1536,
            "supervisor_decision": {"agents": []},
            "skill_level": "intermediate",
        }

        # Time 1000 scoping operations
        start = time.time()
        for _ in range(1000):
            build_scoped_context(large_state, "security_auditor")
        elapsed = time.time() - start

        # Should complete in < 1 second for 1000 iterations
        assert elapsed < 1.0, f"Scoping too slow: {elapsed:.2f}s for 1000 iterations"

    def test_translate_findings_performance(self) -> None:
        """Test that translate_findings handles many findings efficiently."""
        import time

        from app.shared.workflows.context_scope import translate_findings

        # Many findings
        many_findings = [
            {"agent_type": f"agent_{i}", "findings": {"data": f"value_{i}"}} for i in range(20)
        ]

        start = time.time()
        for _ in range(1000):
            translate_findings(many_findings, "target_agent", include_findings=True)
        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0, f"Translation too slow: {elapsed:.2f}s for 1000 iterations"


class TestMemoryTypeMapping:
    """Tests for memory type mapping under various conditions."""

    def test_all_agents_have_consistent_mappings(self) -> None:
        """Test that memory type mappings are consistent with scopes."""
        from app.domains.analysis.workflows.tasks.aggregate_findings import AGENT_MEMORY_TYPE_MAP
        from app.shared.workflows.context_scope import AGENT_SCOPES

        # All agents in memory map should also be in scopes
        for agent in AGENT_MEMORY_TYPE_MAP:
            assert agent in AGENT_SCOPES, f"Agent {agent} in memory map but not in scopes"

    def test_content_extraction_handles_edge_cases(self) -> None:
        """Test content extraction with various edge cases."""
        # None finding
        assert _extract_finding_content("any", None) == ""

        # Empty dict
        assert _extract_finding_content("any", {}) == ""

        # Non-dict finding
        result = _extract_finding_content("any", "just a string")
        assert result == "just a string"

        # Very deeply nested
        nested = {
            "level1": {
                "level2": {"level3": {"level4": "value"}},
                "list": [{"nested": "item"} for _ in range(100)],
            }
        }
        result = _extract_finding_content("unknown", nested)
        assert len(result) <= 2000
