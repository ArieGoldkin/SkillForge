"""Integration tests for Sprint 11 Context Engineering features.

Tests verify the end-to-end behavior of:
- #244: Handle Pattern (SectionExtractor)
- #245: Agent Memory Access (RAG)
- #246: Multi-Agent Context Scoping
- #247: Session Compaction
- #266: Proactive Recall Wiring
- #268: Artifact Loading in Agents
- #269: Store Findings as Memories
- #270: Tutor ContextCompiler Migration
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.agent_memory import MemoryType
from app.domains.analysis.services.context.compaction import CompactionConfig, SessionCompactor
from app.domains.analysis.services.context.section_extractor import SectionExtractor
from app.shared.workflows.context_compiler import create_workflow_compiler
from app.shared.workflows.context_scope import (
    AGENT_SCOPES,
    build_scoped_context,
    translate_findings,
)
from app.domains.analysis.workflows.nodes.agent_router import route_to_agents
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.aggregate_findings import (
    AGENT_MEMORY_TYPE_MAP,
    _extract_finding_content,
    _store_findings_as_memories,
)


class TestContextScopingIntegration:
    """Integration tests for Multi-Agent Context Scoping (#246)."""

    def test_scoping_reduces_state_size_significantly(self) -> None:
        """Test that context scoping achieves significant size reduction."""
        # Create a realistic full state (~50KB+)
        full_state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com/article",
            "content_type": "article",
            "raw_content": "X" * 50000,  # 50KB of content
            "content_ref": {
                "uri": "analysis://test/content",
                "summary": "Test article about Python FastAPI development",
                "size_bytes": 50000,
            },
            "extraction_metadata": {
                "title": "FastAPI Guide",
                "author": "Test Author",
                "word_count": 5000,
            },
            "content_embedding": [0.1] * 1536,  # Full embedding
            "supervisor_decision": {"agents": ["security_auditor", "tech_comparator"]},
            "skill_level": "intermediate",
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"primary_tech": "FastAPI", "alternatives": ["Flask", "Django"]},
                },
                {
                    "agent_type": "security_auditor",
                    "findings": {"security_risks": [{"type": "xss", "severity": "medium"}]},
                },
            ],
        }

        # Test scoping for each agent type
        for agent_type in ["security_auditor", "tech_comparator", "implementation_planner"]:
            scoped = build_scoped_context(full_state, agent_type)

            # Verify size reduction
            full_size = len(str(full_state))
            scoped_size = len(str(scoped))
            reduction_pct = ((full_size - scoped_size) / full_size) * 100

            # Should achieve at least 90% reduction (raw_content + embedding removed)
            assert reduction_pct > 90, (
                f"Agent {agent_type} achieved only {reduction_pct:.1f}% reduction"
            )

            # Verify raw_content never included
            assert "raw_content" not in scoped
            assert "content_embedding" not in scoped

            # Verify essential fields included
            assert "analysis_id" in scoped
            assert "content_ref" in scoped

    def test_all_agents_have_minimal_scopes(self) -> None:
        """Test that all agent scopes are configured with minimal fields."""
        for agent_type, scope in AGENT_SCOPES.items():
            # Should have 3-6 fields typically
            assert len(scope.include) <= 6, (
                f"Agent {agent_type} has too many fields: {len(scope.include)}"
            )
            # Must include analysis_id
            assert "analysis_id" in scope.include
            # Must not include raw_content
            assert "raw_content" not in scope.include

    def test_scoped_state_preserves_content_ref(self) -> None:
        """Test that scoped state includes content_ref handle."""
        state: AnalysisState = {
            "analysis_id": "test-123",
            "content_type": "article",
            "content_ref": {
                "uri": "analysis://test/content",
                "summary": "Article about testing",
                "size_bytes": 5000,
            },
            "raw_content": "Large content...",
            "skill_level": "beginner",
        }

        scoped = build_scoped_context(state, "security_auditor")

        # Content ref should be preserved
        assert "content_ref" in scoped
        assert scoped["content_ref"]["uri"] == "analysis://test/content"
        # Raw content should not be included
        assert "raw_content" not in scoped


class TestProactiveRecallIntegration:
    """Integration tests for Proactive Recall (#266)."""

    @pytest.mark.asyncio
    async def test_route_to_agents_with_memory_injection(self) -> None:
        """Test that routing injects memory for agents with inject_memory=True."""
        state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "content_ref": {
                "uri": "analysis://test/content",
                "summary": "Python security best practices for web applications",
            },
            "raw_content": "Test content about Python security",
            "supervisor_decision": {
                "agents": ["security_auditor"],  # inject_memory=True
                "priority": [0.9],
                "reasoning": "Security analysis needed",
                "confidence": 0.85,
            },
            "skill_level": "intermediate",
        }

        # Mock the memory fetch to return test data
        mock_memory = "## Prior Context\n\n1. Previous SQL injection patterns found..."

        with patch(
            "app.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = mock_memory

            sends = await route_to_agents(state)

            # Should create one Send for security_auditor
            assert len(sends) == 1
            assert sends[0].node == "security_auditor"

            # Memory should be injected into scoped state
            scoped_state = sends[0].arg
            assert "prior_memory" in scoped_state
            assert scoped_state["prior_memory"] == mock_memory

    @pytest.mark.asyncio
    async def test_route_to_agents_no_memory_for_disabled_agents(self) -> None:
        """Test that agents with inject_memory=False don't get memory injected."""
        state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "content_ref": {"uri": "analysis://test/content", "summary": "Test"},
            "raw_content": "Test",
            "supervisor_decision": {
                "agents": ["code_quality_critic"],  # inject_memory=False
                "priority": [0.9],
                "reasoning": "Quality check",
                "confidence": 0.85,
            },
            "skill_level": "intermediate",
        }

        sends = await route_to_agents(state)

        # Should not have prior_memory since inject_memory=False
        assert len(sends) == 1
        scoped_state = sends[0].arg
        assert "prior_memory" not in scoped_state

    @pytest.mark.asyncio
    async def test_route_to_agents_graceful_memory_failure(self) -> None:
        """Test that memory fetch failures don't break routing."""
        state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "content_ref": {"uri": "analysis://test/content", "summary": "Test"},
            "raw_content": "Test",
            "supervisor_decision": {
                "agents": ["security_auditor"],
                "priority": [0.9],
                "reasoning": "Test",
                "confidence": 0.85,
            },
            "skill_level": "intermediate",
        }

        with patch(
            "app.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            # Simulate memory fetch returning empty (error fallback)
            mock_fetch.return_value = ""

            sends = await route_to_agents(state)

            # Routing should still succeed
            assert len(sends) == 1
            assert sends[0].node == "security_auditor"
            # prior_memory should not be in state if empty
            assert "prior_memory" not in sends[0].arg


class TestSessionCompactionIntegration:
    """Integration tests for Session Compaction (#247)."""

    @pytest.mark.asyncio
    async def test_small_history_not_compacted(self) -> None:
        """Test that small conversation history is not compacted."""
        compactor = SessionCompactor(CompactionConfig(max_turns_full=5, summarize_after=10))

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How does FastAPI work?"},
        ]

        result = await compactor.compact(history)

        # Should be unchanged
        assert result.compiled_count == 3
        assert result.messages == history
        assert result.compression_ratio == 1.0
        assert result.summary is None

    @pytest.mark.asyncio
    async def test_large_history_compaction_with_mock_llm(self) -> None:
        """Test that large history triggers compaction."""
        config = CompactionConfig(max_turns_full=2, summarize_after=5)
        compactor = SessionCompactor(config)

        # Create history with 8 messages (exceeds threshold)
        history = [{"role": "user", "content": f"Message {i}"} for i in range(8)]

        with patch.object(compactor, "_summarize_turns", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = "Summary: User asked 6 questions about various topics."

            result = await compactor.compact(history)

            # Should have compacted
            assert result.compiled_count < result.original_count
            assert result.compression_ratio < 1.0
            assert result.summary is not None
            # Recent messages should be preserved
            assert len(result.messages) == 2

    def test_tool_call_preservation(self) -> None:
        """Test that tool calls are preserved during compaction."""
        compactor = SessionCompactor()

        msg_with_tool = {
            "role": "assistant",
            "content": "Searching...",
            "tool_calls": [{"id": "1", "function": {"name": "search"}}],
        }
        msg_without_tool = {"role": "user", "content": "What's the result?"}

        assert compactor._is_tool_call(msg_with_tool) is True
        assert compactor._is_tool_call(msg_without_tool) is False


class TestContextCompilerIntegration:
    """Integration tests for ContextCompiler (#270)."""

    def test_create_tutor_compiler(self) -> None:
        """Test creating tutor workflow compiler."""
        compiler = create_workflow_compiler("tutor")

        assert compiler.system_prompt is not None
        assert "Socratic" in compiler.system_prompt
        assert compiler.agent_identity is not None
        assert "patient" in compiler.agent_identity.lower()

    def test_create_analysis_compiler(self) -> None:
        """Test creating analysis workflow compiler."""
        compiler = create_workflow_compiler("analysis")

        assert compiler.system_prompt is not None
        assert "technical" in compiler.system_prompt.lower()

    @pytest.mark.asyncio
    async def test_compiler_builds_correct_message_structure(self) -> None:
        """Test that compiler produces correct message structure."""
        compiler = create_workflow_compiler("tutor")

        with patch.object(compiler.compactor, "compact", new_callable=AsyncMock) as mock_compact:
            from app.domains.analysis.services.context.compaction import CompiledContext

            mock_compact.return_value = CompiledContext(
                prefix=[],
                messages=[{"role": "user", "content": "Hi"}],
                original_count=1,
                compiled_count=1,
                summary=None,
            )

            messages = await compiler.compile_for_invocation(
                session_history=[{"role": "user", "content": "Hi"}],
                current_input="How do I learn Python?",
                injected_memory=["User prefers examples"],
            )

            # Should have: system + memory + history + current
            assert len(messages) >= 4
            assert messages[0]["role"] == "system"
            assert messages[-1]["role"] == "user"
            assert messages[-1]["content"] == "How do I learn Python?"


class TestMemoryStorageIntegration:
    """Integration tests for Memory Storage (#269)."""

    def test_all_agents_have_memory_type_mapping(self) -> None:
        """Test that all analysis agents have memory type mappings."""
        expected_agents = [
            "security_auditor",
            "tech_comparator",
            "implementation_planner",
            "code_quality_critic",
            "performance_analyst",
            "dependency_mapper",
            "trend_validator",
            "integration_feasibility",
        ]

        for agent in expected_agents:
            assert agent in AGENT_MEMORY_TYPE_MAP
            assert isinstance(AGENT_MEMORY_TYPE_MAP[agent], MemoryType)

    def test_content_extraction_for_all_agents(self) -> None:
        """Test content extraction works for all agent types."""
        test_findings = {
            "security_auditor": {
                "security_risks": [{"risk_type": "xss", "description": "XSS vulnerability"}],
                "recommendation": "Sanitize inputs",
            },
            "tech_comparator": {
                "primary_tech": "FastAPI",
                "alternatives": ["Flask", "Django"],
                "recommendation": "Use FastAPI",
            },
            "implementation_planner": {
                "prerequisites": ["Python 3.11", "PostgreSQL"],
                "recommendation": "Follow guide",
            },
            "performance_analyst": {
                "performance_concerns": "High memory usage",
                "recommendation": "Optimize queries",
            },
            "code_quality_critic": {
                "quality_issues": ["Missing tests", "No docstrings"],
                "recommendation": "Add tests",
            },
        }

        for agent_type, finding in test_findings.items():
            content = _extract_finding_content(agent_type, finding)
            assert len(content) > 0, f"Agent {agent_type} produced empty content"
            assert "Recommendation:" in content

    @pytest.mark.asyncio
    async def test_store_findings_with_mocked_db(self) -> None:
        """Test storing findings with mocked database."""
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

            findings = [
                {
                    "agent_type": "security_auditor",
                    "findings": {"recommendation": "Fix security"},
                    "confidence_score": 0.9,
                },
                {
                    "agent_type": "tech_comparator",
                    "findings": {"primary_tech": "FastAPI"},
                    "confidence_score": 0.85,
                },
            ]

            stored_count = await _store_findings_as_memories(
                analysis_id=str(uuid4()),
                agent_findings=findings,
            )

            # Should store 2 findings
            assert stored_count == 2
            assert mock_service.store.call_count == 2


class TestSectionExtractorIntegration:
    """Integration tests for SectionExtractor (#244)."""

    def test_extract_markdown_sections(self) -> None:
        """Test extracting sections from markdown content."""
        extractor = SectionExtractor()

        content = """# Introduction

This is an introduction to Python.

## Code Example

```python
def hello():
    print("Hello World")
```

## Conclusion

That's all folks!
"""

        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 1
        assert sections.code_blocks[0].language == "python"
        assert len(sections.headings) == 3
        assert sections.word_count > 0

    def test_extract_multiple_code_blocks(self) -> None:
        """Test extracting multiple code blocks."""
        extractor = SectionExtractor()

        content = """# Examples

```python
def foo():
    pass
```

Some text.

```javascript
function bar() {}
```
"""

        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 2
        assert sections.code_blocks[0].language == "python"
        assert sections.code_blocks[1].language == "javascript"

    def test_extract_empty_content(self) -> None:
        """Test extracting from empty content."""
        extractor = SectionExtractor()

        sections = extractor.extract("")

        assert len(sections.code_blocks) == 0
        assert len(sections.headings) == 0
        assert sections.word_count == 0


class TestTranslateFindings:
    """Integration tests for translate_findings function."""

    def test_translate_findings_creates_narrative(self) -> None:
        """Test that translate_findings creates readable narrative."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {"technologies": ["Python", "FastAPI"]},
            },
            {
                "agent_type": "security_auditor",
                "findings": {"security_risks": ["XSS", "SQL Injection"]},
            },
        ]

        narrative = translate_findings(findings, "implementation_planner", include_findings=True)

        assert "Prior Analysis Context" in narrative
        assert "tech_comparator" in narrative
        assert "security_auditor" in narrative

    def test_translate_excludes_same_agent(self) -> None:
        """Test that translate_findings excludes findings from same agent."""
        findings = [
            {"agent_type": "security_auditor", "findings": {"risk": "test"}},
            {"agent_type": "tech_comparator", "findings": {"tech": "Python"}},
        ]

        narrative = translate_findings(findings, "security_auditor")

        # Should not include security_auditor in narrative
        assert "security_auditor" not in narrative
        # Should include tech_comparator
        assert "tech_comparator" in narrative


class TestEndToEndContextFlow:
    """End-to-end tests for the complete context engineering flow."""

    @pytest.mark.asyncio
    async def test_full_context_scoping_flow(self) -> None:
        """Test complete flow: state -> scope -> route."""
        # Step 1: Create full state
        state: AnalysisState = {
            "analysis_id": str(uuid4()),
            "url": "https://example.com",
            "content_type": "article",
            "content_ref": {
                "uri": "analysis://test/content",
                "summary": "Article about Python security",
            },
            "raw_content": "X" * 10000,  # 10KB content
            "content_embedding": [0.1] * 1536,
            "supervisor_decision": {
                "agents": ["security_auditor", "tech_comparator"],
                "priority": [0.9, 0.8],
                "reasoning": "Security and tech analysis",
                "confidence": 0.85,
            },
            "skill_level": "intermediate",
        }

        # Step 2: Route to agents (includes scoping)
        sends = await route_to_agents(state)

        # Should create 2 sends
        assert len(sends) == 2

        # Step 3: Verify each send has scoped state
        for send in sends:
            scoped_state = send.arg
            # Should NOT have raw_content or embedding
            assert "raw_content" not in scoped_state
            assert "content_embedding" not in scoped_state
            # Should have essential fields
            assert "analysis_id" in scoped_state
            assert "content_ref" in scoped_state
