"""Unit tests for agent execution recording functionality.

Tests cover save_agent_finding() and record_agent_execution() functions
in app.domains.analysis.workflows.agents.base, which persist agent execution
results and metadata to the database.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.constants.error_codes import AgentStatus
from app.domains.analysis.workflows.agents.base import record_agent_execution, save_agent_finding


@pytest.fixture
def mock_session():
    """Create a mock database session.

    Note:
        - session.add() is synchronous (MagicMock)
        - session.execute(), commit(), refresh() are async (AsyncMock)
        - scalar_one_or_none() is synchronous but called on result object

    """
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)

    # Mock execute() to return a result with Analysis record
    mock_result = MagicMock()
    mock_analysis = MagicMock()
    mock_analysis.id = uuid.uuid4()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_analysis)
    session.execute = AsyncMock(return_value=mock_result)

    return session


@pytest.fixture
def analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_save_agent_finding_with_success_status(mock_session, analysis_id):
    """Test save_agent_finding() creates record with status='success'."""
    findings_data = {"comparison": "Tool A vs Tool B", "verdict": "Use Tool A"}
    confidence = 0.85
    processing_time = 1234

    with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
        mock_finding = MagicMock()
        mock_finding.id = uuid.uuid4()
        mock_finding.status = AgentStatus.SUCCESS
        mock_finding_class.return_value = mock_finding

        result = await save_agent_finding(
            session=mock_session,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            findings=findings_data,
            confidence_score=confidence,
            processing_time_ms=processing_time,
            status=AgentStatus.SUCCESS,
        )

        # Verify AgentFinding was created with correct parameters
        mock_finding_class.assert_called_once_with(
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            findings=findings_data,
            confidence_score=confidence,
            processing_time_ms=processing_time,
            status=AgentStatus.SUCCESS,
            error_code=None,
            error_message=None,
        )

        # Verify database operations
        mock_session.add.assert_called_once_with(mock_finding)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_finding)

        # Verify result
        assert result == mock_finding
        assert result.status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_save_agent_finding_with_failed_status(mock_session, analysis_id):
    """Test save_agent_finding() creates record with status='failed', error_code, error_message."""
    error_code = "AGENT_TIMEOUT"
    error_message = "Agent execution exceeded 300s timeout"
    processing_time = 300000  # 300 seconds in ms

    with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
        mock_finding = MagicMock()
        mock_finding.id = uuid.uuid4()
        mock_finding.status = AgentStatus.FAILED
        mock_finding.error_code = error_code
        mock_finding.error_message = error_message
        mock_finding_class.return_value = mock_finding

        result = await save_agent_finding(
            session=mock_session,
            analysis_id=analysis_id,
            agent_type="security_auditor",
            findings={},  # Empty dict for failed execution
            processing_time_ms=processing_time,
            status=AgentStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )

        # Verify AgentFinding was created with error fields
        mock_finding_class.assert_called_once_with(
            analysis_id=analysis_id,
            agent_type="security_auditor",
            findings={},
            confidence_score=None,
            processing_time_ms=processing_time,
            status=AgentStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )

        # Verify database operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify result has error fields populated
        assert result.status == AgentStatus.FAILED
        assert result.error_code == error_code
        assert result.error_message == error_message


@pytest.mark.asyncio
async def test_save_agent_finding_with_skipped_status(mock_session, analysis_id):
    """Test save_agent_finding() creates record with status='skipped'."""
    error_code = "AGENT_NO_CODE"
    error_message = "Content has no code to analyze (skipping code_quality_critic)"

    with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
        mock_finding = MagicMock()
        mock_finding.id = uuid.uuid4()
        mock_finding.status = AgentStatus.SKIPPED
        mock_finding.error_code = error_code
        mock_finding.error_message = error_message
        mock_finding_class.return_value = mock_finding

        result = await save_agent_finding(
            session=mock_session,
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            findings={},  # Empty dict for skipped execution
            status=AgentStatus.SKIPPED,
            error_code=error_code,
            error_message=error_message,
        )

        # Verify AgentFinding was created with skipped status
        mock_finding_class.assert_called_once_with(
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            findings={},
            confidence_score=None,
            processing_time_ms=None,
            status=AgentStatus.SKIPPED,
            error_code=error_code,
            error_message=error_message,
        )

        # Verify result
        assert result.status == AgentStatus.SKIPPED
        assert result.error_code == error_code


@pytest.mark.asyncio
async def test_record_agent_execution_success():
    """Test record_agent_execution() helper function records success."""
    analysis_id = str(uuid.uuid4())
    findings_data = {"security_issues": ["XSS vulnerability in input handler"]}
    confidence = 0.92
    processing_time = 2500

    # Create mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock Analysis exists check
    mock_result = MagicMock()
    mock_analysis = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_analysis)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.domains.analysis.workflows.agents.base.get_session_factory"
    ) as mock_session_factory:
        # Mock session factory to return callable that returns context manager
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_factory

        with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
            mock_finding = MagicMock()
            mock_finding_class.return_value = mock_finding

            # Call record_agent_execution (no session parameter - creates its own)
            await record_agent_execution(
                analysis_id=analysis_id,
                agent_type="security_auditor",
                status=AgentStatus.SUCCESS,
                findings=findings_data,
                confidence_score=confidence,
                processing_time_ms=processing_time,
            )

            # Verify AgentFinding was created with correct parameters
            mock_finding_class.assert_called_once()
            call_kwargs = mock_finding_class.call_args.kwargs
            assert call_kwargs["agent_type"] == "security_auditor"
            assert call_kwargs["findings"] == findings_data
            assert call_kwargs["confidence_score"] == confidence
            assert call_kwargs["processing_time_ms"] == processing_time
            assert call_kwargs["status"] == AgentStatus.SUCCESS
            assert call_kwargs["error_code"] is None
            assert call_kwargs["error_message"] is None

            # Verify database operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_record_agent_execution_handles_db_error_gracefully():
    """Test that record_agent_execution() catches and logs DB errors without raising.

    This ensures that database failures during agent execution recording don't
    crash the workflow - they're logged but execution continues.
    """
    analysis_id = str(uuid.uuid4())

    with patch(
        "app.domains.analysis.workflows.agents.base.get_session_factory"
    ) as mock_session_factory:
        # Mock session factory to raise database error when called
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Database connection lost")
        )
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_factory

        with patch("app.domains.analysis.workflows.agents.base.logger") as mock_logger:
            # Should NOT raise exception - error is logged and swallowed
            await record_agent_execution(
                analysis_id=analysis_id,
                agent_type="tech_comparator",
                status=AgentStatus.FAILED,
                error_code="AGENT_LLM_ERROR",
                error_message="LLM API timeout",
            )

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_log_call = mock_logger.error.call_args
            assert "failed_to_record_agent_execution" in error_log_call[0]
            assert error_log_call.kwargs["agent_type"] == "tech_comparator"
            assert error_log_call.kwargs["status"] == AgentStatus.FAILED
            assert "Database connection lost" in error_log_call.kwargs["error"]


@pytest.mark.asyncio
async def test_record_agent_execution_converts_string_analysis_id_to_uuid():
    """Test record_agent_execution() converts analysis_id string to UUID."""
    analysis_id_str = str(uuid.uuid4())

    # Create mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock Analysis exists check
    mock_result = MagicMock()
    mock_analysis = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_analysis)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.domains.analysis.workflows.agents.base.get_session_factory"
    ) as mock_session_factory:
        # Mock session factory
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_factory

        with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
            mock_finding = MagicMock()
            mock_finding_class.return_value = mock_finding

            await record_agent_execution(
                analysis_id=analysis_id_str,  # Pass string
                agent_type="performance_analyst",
                status=AgentStatus.SUCCESS,
                findings={"bottleneck": "N+1 query in user lookup"},
            )

            # Verify AgentFinding was created with UUID object
            call_kwargs = mock_finding_class.call_args.kwargs
            assert isinstance(call_kwargs["analysis_id"], uuid.UUID)
            assert str(call_kwargs["analysis_id"]) == analysis_id_str


@pytest.mark.asyncio
async def test_record_agent_execution_uses_empty_dict_for_none_findings():
    """Test record_agent_execution() uses empty dict when findings=None (for failures)."""
    analysis_id = str(uuid.uuid4())

    # Create mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock Analysis exists check
    mock_result = MagicMock()
    mock_analysis = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_analysis)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.domains.analysis.workflows.agents.base.get_session_factory"
    ) as mock_session_factory:
        # Mock session factory
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_factory

        with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
            mock_finding = MagicMock()
            mock_finding_class.return_value = mock_finding

            # Call with findings=None (common for failures)
            await record_agent_execution(
                analysis_id=analysis_id,
                agent_type="implementation_planner",
                status=AgentStatus.FAILED,
                findings=None,  # Explicitly None
                error_code="AGENT_TIMEOUT",
                error_message="Timeout after 300s",
            )

            # Verify empty dict was used
            call_kwargs = mock_finding_class.call_args.kwargs
            assert call_kwargs["findings"] == {}
            assert call_kwargs["status"] == AgentStatus.FAILED


def test_agent_status_constants():
    """Test AgentStatus has correct constant values."""
    # Verify constants match expected values
    assert AgentStatus.SUCCESS == "success"
    assert AgentStatus.FAILED == "failed"
    assert AgentStatus.SKIPPED == "skipped"

    # Verify all status values are strings
    assert isinstance(AgentStatus.SUCCESS, str)
    assert isinstance(AgentStatus.FAILED, str)
    assert isinstance(AgentStatus.SKIPPED, str)
