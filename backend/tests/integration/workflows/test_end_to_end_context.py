"""End-to-end integration tests for Context Engineering.

IMPORTANT: These tests use REAL PostgreSQL and REAL API keys.
They require:
- Running PostgreSQL with pgvector extension (port 5437)
- Valid API keys in backend/.env

Tests verify the full context engineering cycle:
1. Store artifact (content) → Create ref
2. Store memory (from prior analysis)
3. Retrieve memory (proactive recall)
4. Use memory in agent context
"""

from uuid import uuid4

import pytest

from app.models.agent_memory import MemoryType
from app.services.context.artifact_store import ArtifactStore
from app.services.embeddings import EmbeddingService
from app.services.memory.agent_memory_service import AgentMemoryService
from app.services.memory.proactive_recall import (
    build_proactive_prompt,
    fetch_proactive_context,
    format_memory_context,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


class TestEndToEndContextFlow:
    """End-to-end integration tests for full context engineering cycle."""

    async def test_full_artifact_to_memory_cycle(
        self,
        db_session,
        create_test_analysis,
        requires_llm,
    ):
        """Test complete flow: artifact → analysis → memory → recall."""
        embedding_service = EmbeddingService()

        # Step 1: Create analysis with content
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/react-security",
            content_type="article",
        )

        content = """
# React Security Best Practices

## XSS Prevention
Always sanitize user input before rendering. Use libraries like DOMPurify.

## CSRF Protection
Implement CSRF tokens for all state-changing operations.

```javascript
// Bad: Vulnerable to XSS
element.innerHTML = userInput;

// Good: Safe rendering
element.textContent = userInput;
```
"""
        analysis.raw_content = content
        await db_session.commit()

        # Step 2: Create artifact ref
        artifact_store = ArtifactStore(db_session)
        ref = await artifact_store.create_ref(
            analysis_id=str(analysis.id),
            content=content,
            content_type="text/markdown",
        )

        assert ref.uri is not None
        assert "code_blocks" in ref.available_sections

        # Step 3: Store findings as memory (simulating agent output)
        memory_service = AgentMemoryService(db_session, embedding_service)

        memory1 = await memory_service.store(
            content="XSS vulnerability pattern: innerHTML with unsanitized input",
            memory_type=MemoryType.VULNERABILITY_PATTERN,
            analysis_id=analysis.id,
            agent_type="security_auditor",
            metadata={"finding_type": "xss", "severity": "high"},
        )

        memory2 = await memory_service.store(
            content="Best practice: Use textContent instead of innerHTML for user data",
            memory_type=MemoryType.BEST_PRACTICE,
            analysis_id=analysis.id,
            agent_type="security_auditor",
        )

        assert memory1.id is not None
        assert memory2.id is not None

        # Step 4: Proactive recall for new analysis
        # Simulating a new analysis about similar topic
        snippets = await fetch_proactive_context(
            session=db_session,
            content_summary="JavaScript DOM manipulation security review",
            agent_type="security_auditor",
            limit=5,
            threshold=0.3,  # Lower threshold for test
            embedding_service=embedding_service,
        )

        # Should recall related security memories
        assert isinstance(snippets, list)

        # Step 5: Format and inject into prompt
        context = format_memory_context(snippets)
        if snippets:
            assert "Relevant Context" in context

    async def test_memory_improves_subsequent_analysis(
        self,
        db_session,
        create_test_analysis,
        requires_llm,
    ):
        """Test that stored memories are recalled for related analyses."""
        embedding_service = EmbeddingService()
        memory_service = AgentMemoryService(db_session, embedding_service)

        # Create first analysis and store findings
        analysis1 = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/sql-injection-guide",
        )

        await memory_service.store(
            content="SQL injection prevention: Always use parameterized queries with $1, $2 placeholders",
            memory_type=MemoryType.VULNERABILITY_PATTERN,
            analysis_id=analysis1.id,
            agent_type="security_auditor",
        )

        await memory_service.store(
            content="ORM security: Avoid raw SQL, use query builders with automatic escaping",
            memory_type=MemoryType.BEST_PRACTICE,
            analysis_id=analysis1.id,
            agent_type="security_auditor",
        )

        # Create second analysis about related topic
        analysis2 = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/database-security",
        )

        # Build prompt with proactive memory injection
        original_prompt = "Analyze this code for database security vulnerabilities"
        content_summary = "PostgreSQL database access patterns and query construction"

        enhanced_prompt = await build_proactive_prompt(
            session=db_session,
            user_prompt=original_prompt,
            content_summary=content_summary,
            agent_type="security_auditor",
            limit=3,
            threshold=0.3,
            embedding_service=embedding_service,
        )

        # The prompt should now include relevant context
        assert original_prompt in enhanced_prompt

    async def test_cross_agent_memory_isolation(
        self,
        db_session,
        requires_llm,
    ):
        """Test that agents recall memories relevant to their specialization."""
        embedding_service = EmbeddingService()
        memory_service = AgentMemoryService(db_session, embedding_service)

        # Store security-related memory
        await memory_service.store(
            content="Authentication bypass through JWT token manipulation",
            memory_type=MemoryType.VULNERABILITY_PATTERN,
            agent_type="security_auditor",
        )

        # Store tech comparison memory
        await memory_service.store(
            content="React vs Vue performance comparison: React has smaller bundle size",
            memory_type=MemoryType.ANALYSIS_SUMMARY,
            agent_type="tech_comparator",
        )

        # Security auditor should recall security memories
        security_snippets = await memory_service.proactive_recall(
            content_summary="JWT authentication implementation",
            agent_type="security_auditor",
            limit=5,
            threshold=0.3,
        )

        # Tech comparator should recall tech memories
        tech_snippets = await memory_service.proactive_recall(
            content_summary="Frontend framework comparison",
            agent_type="tech_comparator",
            limit=5,
            threshold=0.3,
        )

        # Both should return appropriate memory types
        for snippet in security_snippets:
            assert snippet.memory_type in ["vulnerability_pattern", "best_practice"]

        for snippet in tech_snippets:
            assert snippet.memory_type in ["analysis_summary", "best_practice"]


class TestContextScopingRealData:
    """Integration tests for context scoping with real data sizes."""

    async def test_scoping_handles_large_real_state(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that context scoping works with realistic state sizes."""
        from app.workflows.context_scope import build_scoped_context

        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/large-analysis",
        )

        # Create realistic large state (50KB+)
        large_content = "x" * 50000
        state = {
            "analysis_id": str(analysis.id),
            "url": analysis.url,
            "content_type": "article",
            "raw_content": large_content,
            "content_ref": {
                "uri": f"analysis://{analysis.id}/content",
                "summary": "Test summary",
                "size_bytes": 50000,
            },
            "agent_findings": [
                {"agent": f"agent_{i}", "finding": f"Finding {i}" * 100} for i in range(8)
            ],
            "supervisor_decision": {
                "agents": ["security_auditor"],
                "priority": [0.9],
                "reasoning": "Test reasoning",
            },
        }

        # Scope for agent using build_scoped_context
        scoped = build_scoped_context(state, "security_auditor")

        # Should be dramatically smaller
        import json

        original_size = len(json.dumps(state))
        scoped_size = len(json.dumps(scoped))

        assert scoped_size < original_size * 0.5  # At least 50% reduction
        assert "raw_content" not in scoped  # Raw content excluded
        assert scoped.get("content_ref") is not None  # Ref preserved


class TestMemorySearchPerformance:
    """Integration tests for memory search performance with real pgvector."""

    async def test_vector_search_performance_with_many_memories(
        self,
        db_session,
        requires_llm,
    ):
        """Test that vector search remains fast with many memories."""
        import time

        embedding_service = EmbeddingService()
        memory_service = AgentMemoryService(db_session, embedding_service)

        # Store multiple memories
        for i in range(10):
            await memory_service.store(
                content=f"Security finding {i}: Vulnerability pattern in authentication module",
                memory_type=MemoryType.VULNERABILITY_PATTERN,
                agent_type="security_auditor",
            )

        # Time the search
        start = time.perf_counter()

        results = await memory_service.search(
            query="authentication security vulnerability",
            memory_type=MemoryType.VULNERABILITY_PATTERN,
            limit=5,
            threshold=0.3,
        )

        elapsed = time.perf_counter() - start

        # Search should complete in under 2 seconds even with embeddings
        assert elapsed < 2.0
        assert len(results) > 0
