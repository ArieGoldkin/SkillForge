"""Integration tests for supervisor node.

These tests require Ollama running with llama3.1:8b model.
Tests are marked with @pytest.mark.external and @pytest.mark.slow.
"""

import asyncio

import pytest

from app.workflows.nodes.supervisor import supervisor_route


@pytest.fixture
def requires_ollama():
    """Skip test if Ollama is not available."""
    import httpx

    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code != 200:
            pytest.skip("Ollama not responding")
    except Exception:
        pytest.skip("Ollama not available - ensure it's running on localhost:11434")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)  # 1 minute max timeout
async def test_supervisor_route_with_tech_content(requires_ollama) -> None:
    """Test supervisor selects tech-related agents for technology content."""
    content = """
    React is a popular JavaScript library for building user interfaces.
    In this article, we compare React with Vue.js and Angular.
    We discuss performance characteristics, developer experience, and ecosystem.
    """

    result = await asyncio.wait_for(
        supervisor_route(
            content=content,
            content_type="article",
            analysis_id="test-supervisor-tech-1",
        ),
        timeout=45.0,
    )

    # Verify supervisor decision structure
    assert "supervisor_decision" in result
    decision = result["supervisor_decision"]
    assert "agents" in decision
    assert "priority" in decision
    assert "reasoning" in decision

    # Verify at least one agent was selected (should include tech_comparator)
    assert len(decision["agents"]) > 0
    assert isinstance(decision["agents"], list)
    assert isinstance(decision["priority"], list)
    assert len(decision["agents"]) == len(decision["priority"])


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_supervisor_route_with_security_content(requires_ollama) -> None:
    """Test supervisor selects security-related agents for security content."""
    content = """
    Security best practices for API development:
    - Always validate input
    - Use authentication tokens
    - Implement rate limiting
    - Sanitize user input to prevent SQL injection
    - Use HTTPS for all communications
    """

    result = await asyncio.wait_for(
        supervisor_route(
            content=content,
            content_type="article",
            analysis_id="test-supervisor-security-1",
        ),
        timeout=45.0,
    )

    decision = result["supervisor_decision"]
    assert len(decision["agents"]) > 0

    # Should likely select security_auditor
    agent_names = decision["agents"]
    # Note: We don't assert specific agents since LLM selection may vary
    # Just verify that agents were selected


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_supervisor_route_with_implementation_content(requires_ollama) -> None:
    """Test supervisor selects implementation-related agents for tutorial content."""
    content = """
    Step-by-step guide to implementing authentication in FastAPI:
    1. Install dependencies
    2. Create user model
    3. Implement password hashing
    4. Create JWT token generation
    5. Add protected routes
    6. Test endpoints
    """

    result = await asyncio.wait_for(
        supervisor_route(
            content=content,
            content_type="article",
            analysis_id="test-supervisor-implementation-1",
        ),
        timeout=45.0,
    )

    decision = result["supervisor_decision"]
    assert len(decision["agents"]) > 0
    # Should likely select implementation_planner


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_supervisor_route_different_content_types(requires_ollama) -> None:
    """Test supervisor works with different content types."""
    content = "This is a test article about web development and best practices."

    for content_type in ["article", "video", "repo"]:
        result = await asyncio.wait_for(
            supervisor_route(
                content=content,
                content_type=content_type,
                analysis_id=f"test-supervisor-{content_type}",
            ),
            timeout=45.0,
        )

        decision = result["supervisor_decision"]
        assert "agents" in decision
        assert "priority" in decision
        # Supervisor should handle all content types


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_supervisor_route_long_content(requires_ollama) -> None:
    """Test supervisor handles long content (should truncate to 2000 chars)."""
    # Create content longer than 2000 chars
    long_content = "This is a long article. " * 200  # ~5000 chars

    result = await asyncio.wait_for(
        supervisor_route(
            content=long_content,
            content_type="article",
            analysis_id="test-supervisor-long",
        ),
        timeout=45.0,
    )

    # Should still work with truncated content
    decision = result["supervisor_decision"]
    assert "agents" in decision


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_supervisor_route_simple_content(requires_ollama) -> None:
    """Test supervisor with very simple content (may select no agents)."""
    simple_content = "Hello world."

    result = await asyncio.wait_for(
        supervisor_route(
            content=simple_content,
            content_type="article",
            analysis_id="test-supervisor-simple",
        ),
        timeout=45.0,
    )

    decision = result["supervisor_decision"]
    # May select no agents or few agents for very simple content
    assert "agents" in decision
    assert isinstance(decision["agents"], list)
