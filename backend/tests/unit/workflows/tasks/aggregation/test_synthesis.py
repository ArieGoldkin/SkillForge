"""Unit tests for synthesis LLM functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.types import AnalysisID
from app.workflows.tasks.aggregation.synthesis import (
    create_synthesis_agent,
    synthesize_with_llm,
)
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights


@pytest.fixture
def sample_analysis_id() -> str:
    """Sample analysis ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_validated_findings() -> list[dict[str, object]]:
    """Sample validated agent findings."""
    return [
        {
            "agent_type": "tech_comparator",
            "findings": {
                "primary_tech": "LangGraph",
                "alternatives": ["LangChain Agents"],
                "recommendation": "Use LangGraph for state management",
                "confidence_score": 0.85,
            },
        },
        {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": [
                    {
                        "risk_type": "authentication",
                        "severity": "high",
                        "description": "Missing API authentication",
                        "mitigation": "Implement JWT tokens",
                    }
                ],
                "recommendation": "Address high-severity risks first",
                "confidence_score": 0.88,
            },
        },
    ]


@pytest.fixture
def sample_conflicts() -> list[dict[str, str]]:
    """Sample detected conflicts."""
    return [
        {
            "agent_1": "tech_comparator",
            "agent_2": "security_auditor",
            "conflict": "tech_comparator recommends adoption, security_auditor raises security concerns",
        }
    ]


@pytest.fixture
def sample_confidence_scores() -> dict[str, float]:
    """Sample confidence scores."""
    return {
        "tech_comparator": 0.85,
        "security_auditor": 0.88,
    }


@pytest.fixture
def sample_llm_response() -> dict[str, object]:
    """Sample LLM synthesis response."""
    return {
        "executive_summary": (
            "LangGraph provides powerful state management for workflows. "
            "Security authentication must be implemented before production deployment. "
            "The technology is mature but requires careful security configuration."
        ),
        "key_findings": [
            "LangGraph offers superior state management compared to alternatives",
            "High-severity authentication gap requires immediate attention",
            "Implementation feasible with proper security controls",
        ],
        "synthesis": {
            "technical_analysis": "LangGraph provides graph-based workflow capabilities...",
            "implementation_guidance": "1. Install LangGraph\n2. Implement authentication\n3. Configure security",
            "risk_assessment": "- High: Missing authentication\n- Medium: Integration complexity",
            "recommendations": "- Implement JWT authentication\n- Use LangGraph for workflows",
        },
        "conflicts_resolved": [
            {
                "conflict": "tech_comparator recommends adoption, security_auditor raises concerns",
                "resolution": "Adopt LangGraph with mandatory security controls",
                "priority_agent": "security_auditor",
                "reasoning": "Security concerns must be addressed before technology adoption",
            }
        ],
        "coverage_gaps": [],
        "cross_domain_connections": [
            {
                "domains": ["technology", "security"],
                "connection": "Technology adoption requires security implementation",
                "agents_involved": ["tech_comparator", "security_auditor"],
            }
        ],
        "coverage_score": 0.25,
    }


class TestCreateSynthesisAgent:
    """Test synthesis agent creation."""

    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    def test_create_synthesis_agent_calls_create_structured_agent(
        self, mock_create_structured_agent: MagicMock
    ):
        """Test that create_synthesis_agent calls create_structured_agent with correct args."""
        mock_agent = MagicMock()
        mock_create_structured_agent.return_value = mock_agent

        # Import and call the actual function (don't mock it)
        result = create_synthesis_agent()

        # Verify create_structured_agent was called
        mock_create_structured_agent.assert_called_once()
        call_kwargs = mock_create_structured_agent.call_args.kwargs

        # Verify system_prompt was passed
        # Issue #304: Prompt redesigned for triple-purpose artifacts
        assert "system_prompt" in call_kwargs
        system_prompt_lower = call_kwargs["system_prompt"].lower()
        assert "triple-purpose" in system_prompt_lower
        assert "executive_summary" in system_prompt_lower  # Required section

        # Verify response_schema is AggregatedInsights
        assert "response_schema" in call_kwargs
        assert call_kwargs["response_schema"] == AggregatedInsights

        # Verify result is the mock agent
        assert result == mock_agent

    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    def test_create_synthesis_agent_returns_runnable(self, mock_create_structured_agent: MagicMock):
        """Test that create_synthesis_agent returns a Runnable."""
        mock_agent = MagicMock()
        mock_create_structured_agent.return_value = mock_agent

        result = create_synthesis_agent()

        # Verify result is returned
        assert result is not None
        assert result == mock_agent


class TestSynthesizeWithLLM:
    """Test LLM synthesis function."""

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    @patch("app.workflows.tasks.aggregation.synthesis.extract_structured_response")
    async def test_synthesize_with_llm_success(
        self,
        mock_extract_structured_response: MagicMock,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test successful LLM synthesis flow."""
        # Setup mocks
        formatted_findings = "Formatted findings text"
        mock_format_findings.return_value = formatted_findings

        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        user_prompt = "User prompt text"
        mock_build_prompt.return_value = user_prompt

        mock_invoke_result = {"result": "agent_output"}
        mock_invoke_agent.return_value = mock_invoke_result

        mock_extract_structured_response.return_value = sample_llm_response

        # Execute the actual synthesize_with_llm function (not mocked)
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify format_findings_for_llm was called with correct args
        mock_format_findings.assert_called_once_with(
            sample_validated_findings, sample_conflicts, sample_confidence_scores
        )

        # Verify create_synthesis_agent was called
        mock_create_agent.assert_called_once()

        # Verify build_synthesis_user_prompt was called with formatted findings
        mock_build_prompt.assert_called_once_with(formatted_findings=formatted_findings)

        # Verify invoke_agent was called with correct structure
        mock_invoke_agent.assert_called_once()
        invoke_call_kwargs = mock_invoke_agent.call_args.kwargs

        assert invoke_call_kwargs["agent"] == mock_agent
        assert "input_messages" in invoke_call_kwargs
        assert invoke_call_kwargs["input_messages"]["messages"][0]["role"] == "user"
        assert invoke_call_kwargs["input_messages"]["messages"][0]["content"] == user_prompt
        assert invoke_call_kwargs["analysis_id"] == sample_analysis_id
        assert invoke_call_kwargs["agent_type"] == "aggregation"
        assert "timeout" in invoke_call_kwargs

        # Verify extract_structured_response was called
        mock_extract_structured_response.assert_called_once_with(mock_invoke_result, "aggregation")

        # Verify result matches expected response
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    async def test_synthesize_with_llm_timeout_error(
        self,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
    ):
        """Test synthesize_with_llm raises TimeoutError on agent timeout."""
        # Setup mocks
        mock_format_findings.return_value = "Formatted findings"
        mock_create_agent.return_value = MagicMock()
        mock_build_prompt.return_value = "User prompt"

        # Mock invoke_agent to raise TimeoutError
        mock_invoke_agent.side_effect = TimeoutError("Agent invocation timed out")

        # Execute and verify TimeoutError is raised
        with pytest.raises(TimeoutError, match="Agent invocation timed out"):
            await synthesize_with_llm(
                validated_findings=sample_validated_findings,
                conflicts=sample_conflicts,
                confidence_scores=sample_confidence_scores,
                analysis_id=sample_analysis_id,
            )

        # Verify invoke_agent was called before timeout
        assert mock_invoke_agent.called

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    async def test_synthesize_with_llm_agent_failure(
        self,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
    ):
        """Test synthesize_with_llm raises Exception on agent failure."""
        # Setup mocks
        mock_format_findings.return_value = "Formatted findings"
        mock_create_agent.return_value = MagicMock()
        mock_build_prompt.return_value = "User prompt"

        # Mock invoke_agent to raise generic Exception
        mock_invoke_agent.side_effect = Exception("LLM API failure")

        # Execute and verify Exception is raised
        with pytest.raises(Exception, match="LLM API failure"):
            await synthesize_with_llm(
                validated_findings=sample_validated_findings,
                conflicts=sample_conflicts,
                confidence_scores=sample_confidence_scores,
                analysis_id=sample_analysis_id,
            )

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    @patch("app.workflows.tasks.aggregation.synthesis.extract_structured_response")
    async def test_synthesize_with_llm_empty_findings(
        self,
        mock_extract_structured_response: MagicMock,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_llm_response: dict[str, object],
    ):
        """Test synthesize_with_llm with empty findings."""
        # Setup mocks
        mock_format_findings.return_value = "No findings available"
        mock_create_agent.return_value = MagicMock()
        mock_build_prompt.return_value = "User prompt"
        mock_invoke_agent.return_value = {"result": "agent_output"}
        mock_extract_structured_response.return_value = sample_llm_response

        # Execute with empty findings
        result = await synthesize_with_llm(
            validated_findings=[],
            conflicts=[],
            confidence_scores={},
            analysis_id=sample_analysis_id,
        )

        # Verify all steps were executed
        mock_format_findings.assert_called_once_with([], [], {})
        mock_create_agent.assert_called_once()
        mock_build_prompt.assert_called_once()
        mock_invoke_agent.assert_called_once()
        mock_extract_structured_response.assert_called_once()

        # Verify result is returned
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    @patch("app.workflows.tasks.aggregation.synthesis.extract_structured_response")
    async def test_synthesize_with_llm_many_conflicts(
        self,
        mock_extract_structured_response: MagicMock,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test synthesize_with_llm with multiple conflicts."""
        # Setup many conflicts
        conflicts = [
            {"agent_1": "tech_comparator", "agent_2": "security_auditor", "conflict": "Conflict 1"},
            {
                "agent_1": "implementation_planner",
                "agent_2": "performance_analyst",
                "conflict": "Conflict 2",
            },
            {
                "agent_1": "dependency_mapper",
                "agent_2": "trend_validator",
                "conflict": "Conflict 3",
            },
        ]

        # Setup mocks
        mock_format_findings.return_value = "Formatted findings with conflicts"
        mock_create_agent.return_value = MagicMock()
        mock_build_prompt.return_value = "User prompt"
        mock_invoke_agent.return_value = {"result": "agent_output"}
        mock_extract_structured_response.return_value = sample_llm_response

        # Execute
        result = await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify conflicts were passed to format_findings_for_llm
        format_call_args = mock_format_findings.call_args
        assert len(format_call_args.args[1]) == 3  # 3 conflicts

        # Verify result is returned
        assert result == sample_llm_response

    @pytest.mark.asyncio
    @patch("app.workflows.tasks.aggregation.synthesis.format_findings_for_llm")
    @patch("app.workflows.tasks.aggregation.synthesis.create_structured_agent")
    @patch("app.workflows.tasks.aggregation.synthesis.build_synthesis_user_prompt")
    @patch("app.workflows.tasks.aggregation.synthesis.invoke_agent", new_callable=AsyncMock)
    @patch("app.workflows.tasks.aggregation.synthesis.extract_structured_response")
    async def test_synthesize_with_llm_uses_synthesis_timeout(
        self,
        mock_extract_structured_response: MagicMock,
        mock_invoke_agent: AsyncMock,
        mock_build_prompt: MagicMock,
        mock_create_agent: MagicMock,
        mock_format_findings: MagicMock,
        sample_analysis_id: AnalysisID,
        sample_validated_findings: list[dict[str, object]],
        sample_conflicts: list[dict[str, str]],
        sample_confidence_scores: dict[str, float],
        sample_llm_response: dict[str, object],
    ):
        """Test that synthesize_with_llm uses SYNTHESIS_TIMEOUT from centralized config."""
        # Setup mocks
        mock_format_findings.return_value = "Formatted findings"
        mock_create_agent.return_value = MagicMock()
        mock_build_prompt.return_value = "User prompt"
        mock_invoke_agent.return_value = {"result": "agent_output"}
        mock_extract_structured_response.return_value = sample_llm_response

        # Execute
        await synthesize_with_llm(
            validated_findings=sample_validated_findings,
            conflicts=sample_conflicts,
            confidence_scores=sample_confidence_scores,
            analysis_id=sample_analysis_id,
        )

        # Verify invoke_agent was called with timeout parameter
        invoke_call_kwargs = mock_invoke_agent.call_args.kwargs
        assert "timeout" in invoke_call_kwargs

        # Import SYNTHESIS_TIMEOUT to verify it's the correct value
        from app.core.timeout_config import SYNTHESIS_TIMEOUT

        assert invoke_call_kwargs["timeout"] == SYNTHESIS_TIMEOUT
