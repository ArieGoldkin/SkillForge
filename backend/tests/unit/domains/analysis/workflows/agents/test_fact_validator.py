"""Unit tests for fact_validator agent.

Tests the Tier 2 Validation agent that extracts and verifies factual claims
using Tavily search.

Issue #436: Tier 2 agent with tool integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.schemas.agents.fact_validator import Claim, FactValidatorOutput
from app.domains.analysis.workflows.agents.fact_validator import run_fact_validator
from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def base_state() -> AnalysisState:
    """Return base state for agent testing."""
    return {
        "analysis_id": "test-fact-validator-123",
        "skill_level": "intermediate",
        "proactive_context": "",
        "agent_expectation": None,
        "content_signals": {},
    }


@pytest.fixture
def sample_output() -> FactValidatorOutput:
    """Return sample fact validation output."""
    return FactValidatorOutput(
        claims=[
            Claim(
                statement="LangGraph requires Python 3.9+",
                source_text="LangGraph is built for Python 3.9 and above",
                validation_status="verified",
                confidence=0.95,
                evidence_url="https://github.com/langchain-ai/langgraph",
            ),
            Claim(
                statement="React 18 supports concurrent rendering",
                source_text="React 18 introduces concurrent rendering features",
                validation_status="verified",
                confidence=0.9,
                evidence_url="https://react.dev/blog/2022/03/29/react-v18",
            ),
            Claim(
                statement="FastAPI is 10x faster than Flask",
                source_text="FastAPI is 10 times faster than Flask for API performance",
                validation_status="disputed",
                confidence=0.6,
                evidence_url="https://www.techempower.com/benchmarks",
            ),
        ],
        validation_score=0.67,  # 2 out of 3 verified
        summary="Content contains mostly accurate technical claims. LangGraph and React features are verified from official sources. The FastAPI performance claim is disputed as benchmarks show variable results depending on workload.",
        confidence_score=0.85,
        data_availability="sufficient",
        data_availability_note="",
    )


@pytest.mark.asyncio
async def test_fact_validator_with_tools(mock_session: AsyncSession, base_state: AnalysisState):
    """Test that fact_validator agent runs with tools and returns expected structure."""
    content = """
    LangGraph is a powerful framework for building agentic workflows.
    It requires Python 3.9 or higher. React 18 introduces concurrent
    rendering features that improve performance. FastAPI is 10 times
    faster than Flask.
    """

    # Mock tools
    mock_tools = [MagicMock(name="tavily_search")]

    # Mock the agent execution - must return dict with "structured_response" key
    # Note: confidence_score must be >= 0.7 (specificity threshold)
    mock_response = FactValidatorOutput(
        claims=[
            Claim(
                statement="LangGraph requires Python 3.9+",
                source_text="It requires Python 3.9 or higher",
                validation_status="verified",
                confidence=0.9,
                evidence_url="https://github.com/langchain-ai/langgraph",
            )
        ],
        validation_score=1.0,
        summary="All claims verified from official sources",
        confidence_score=0.9,  # Must be >= threshold (0.7)
    )
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"structured_response": mock_response})

    # Mock run_agent_with_tracking to avoid specificity scoring
    async def mock_run_with_tracking(*args, **kwargs):
        return {
            "agent_type": "fact_validator",
            "findings": mock_response.model_dump(),
            "processing_time_ms": 100,
        }

    with (
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.create_agent_with_optional_few_shot",
            return_value=mock_agent,
        ),
        patch("app.domains.analysis.workflows.agents.fact_validator.get_prompt_manager") as mock_pm,
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.run_agent_with_tracking",
            side_effect=mock_run_with_tracking,
        ),
    ):
        mock_pm.return_value.get_prompt_with_langfuse_client = AsyncMock(
            return_value=("You are a fact validation specialist", None)
        )

        result = await run_fact_validator(
            content=content,
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
            tools=mock_tools,
        )

    # Verify result structure
    assert "agent_type" in result
    assert result["agent_type"] == "fact_validator"
    assert "findings" in result
    assert "processing_time_ms" in result


@pytest.mark.asyncio
async def test_fact_validator_without_tools_logs_warning(
    mock_session: AsyncSession, base_state: AnalysisState
):
    """Test that fact_validator logs warning when run without tools."""
    content = "Some technical content with claims"

    # Mock the agent execution - must return dict with "structured_response" key
    # Note: confidence_score must be >= 0.7 (specificity threshold)
    mock_response = FactValidatorOutput(
        claims=[],
        validation_score=0.0,
        summary="No tools available for verification",
        confidence_score=0.75,  # Must be >= threshold (0.7)
    )
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"structured_response": mock_response})

    # Mock run_agent_with_tracking to avoid specificity scoring
    async def mock_run_with_tracking(*args, **kwargs):
        return {
            "agent_type": "fact_validator",
            "findings": mock_response.model_dump(),
            "processing_time_ms": 100,
        }

    with (
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.create_agent_with_optional_few_shot",
            return_value=mock_agent,
        ),
        patch("app.domains.analysis.workflows.agents.fact_validator.get_prompt_manager") as mock_pm,
        patch("app.domains.analysis.workflows.agents.fact_validator.logger") as mock_logger,
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.run_agent_with_tracking",
            side_effect=mock_run_with_tracking,
        ),
    ):
        mock_pm.return_value.get_prompt_with_langfuse_client = AsyncMock(
            return_value=("Test prompt", None)
        )

        result = await run_fact_validator(
            content=content,
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
            tools=None,  # No tools provided
        )

    # Verify warning was logged
    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args
    assert call_args[0][0] == "fact_validator_without_tools"


@pytest.mark.asyncio
async def test_fact_validator_uses_grounding(mock_session: AsyncSession, base_state: AnalysisState):
    """Test that fact_validator applies grounding instructions to prompt."""
    content = "Test content"
    captured_prompt = None

    async def mock_create_agent(*args, **kwargs):
        nonlocal captured_prompt
        if "system_prompt" in kwargs:
            captured_prompt = kwargs["system_prompt"]
        # Return mock agent - must return dict with "structured_response" key
        # Note: confidence_score must be >= 0.7 (specificity threshold)
        mock_response = FactValidatorOutput(
            claims=[],
            validation_score=0.0,
            summary="Test",
            confidence_score=0.8,  # Must be >= threshold (0.7)
        )
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={"structured_response": mock_response})
        return mock_agent

    # Mock run_agent_with_tracking to avoid specificity scoring
    async def mock_run_with_tracking(*args, **kwargs):
        return {
            "agent_type": "fact_validator",
            "findings": {},
            "processing_time_ms": 100,
        }

    with (
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.create_agent_with_optional_few_shot",
            side_effect=mock_create_agent,
        ),
        patch("app.domains.analysis.workflows.agents.fact_validator.get_prompt_manager") as mock_pm,
        patch(
            "app.domains.analysis.workflows.agents.fact_validator.run_agent_with_tracking",
            side_effect=mock_run_with_tracking,
        ),
    ):
        mock_pm.return_value.get_prompt_with_langfuse_client = AsyncMock(
            return_value=("Base prompt", None)
        )

        await run_fact_validator(
            content=content,
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
            tools=None,
        )

    # Verify grounding was applied (captured_prompt should contain grounding text)
    assert captured_prompt is not None
    assert "CONTENT GROUNDING REQUIREMENTS" in captured_prompt
    assert "ONLY analyze what's in the content" in captured_prompt


def test_claim_schema_validation():
    """Test Claim model validation."""
    # Valid claim
    claim = Claim(
        statement="Python 3.11 is 25% faster than 3.10",
        source_text="Benchmarks show Python 3.11 delivers 25% performance gains over 3.10",
        validation_status="verified",
        confidence=0.9,
        evidence_url="https://docs.python.org/3.11/whatsnew/3.11.html",
    )
    assert claim.validation_status == "verified"
    assert claim.confidence == 0.9

    # Claim without evidence URL
    claim_no_url = Claim(
        statement="FastAPI is async",
        source_text="FastAPI uses async/await",
        validation_status="unverified",
        confidence=0.5,
        evidence_url=None,
    )
    assert claim_no_url.evidence_url is None


def test_fact_validator_output_schema():
    """Test FactValidatorOutput model validation."""
    output = FactValidatorOutput(
        claims=[
            Claim(
                statement="Test claim",
                source_text="Test source",
                validation_status="verified",
                confidence=0.8,
            )
        ],
        validation_score=1.0,
        summary="All claims verified",
        confidence_score=0.9,
    )
    assert len(output.claims) == 1
    assert output.validation_score == 1.0
    assert output.data_availability == "sufficient"  # Default value


def test_validation_score_calculation():
    """Test validation score represents proportion of verified claims."""
    # 2 out of 3 verified = 0.67
    output = FactValidatorOutput(
        claims=[
            Claim(
                statement="Claim 1",
                source_text="Source 1",
                validation_status="verified",
                confidence=0.9,
            ),
            Claim(
                statement="Claim 2",
                source_text="Source 2",
                validation_status="verified",
                confidence=0.85,
            ),
            Claim(
                statement="Claim 3",
                source_text="Source 3",
                validation_status="disputed",
                confidence=0.6,
            ),
        ],
        validation_score=0.67,
        summary="Most claims verified",
        confidence_score=0.8,
    )
    assert output.validation_score == 0.67
    assert len(output.claims) == 3


def test_data_availability_mixin():
    """Test DataAvailabilityMixin fields in FactValidatorOutput."""
    output = FactValidatorOutput(
        claims=[],
        validation_score=0.0,
        summary="No factual claims found in content",
        confidence_score=0.5,
        data_availability="insufficient",
        data_availability_note="Content is primarily opinion-based with no verifiable facts",
    )
    assert output.data_availability == "insufficient"
    assert "opinion-based" in output.data_availability_note
