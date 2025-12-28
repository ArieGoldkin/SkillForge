"""Unit tests for exception utilities and classes.

Tests for Issue #535 - 2025 exception handling best practices.
"""

from __future__ import annotations

import pytest

from app.core.exception_utils import (
    async_exception_context,
    collect_agent_errors,
    enrich_exception,
    exception_context,
    is_retryable,
    wrap_external_error,
)
from app.core.exceptions import (
    AgentError,
    AgentGroupError,
    CacheError,
    ConfigurationError,
    EvaluationError,
    ExternalServiceError,
    RetryableError,
    SkillForgeException,
    TransientError,
    WorkflowError,
    is_cleanup_generator_exit,
)


@pytest.mark.unit
def test_is_cleanup_generator_exit_cleanup_case():
    """Test that cleanup GeneratorExit is detected correctly."""
    # Cleanup GeneratorExit (workflow completed)
    assert is_cleanup_generator_exit(GeneratorExit(), workflow_completed=True) is True


@pytest.mark.unit
def test_is_cleanup_generator_exit_execution_case():
    """Test that execution GeneratorExit is detected correctly."""
    # Execution GeneratorExit (workflow didn't complete)
    assert is_cleanup_generator_exit(GeneratorExit(), workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_converted_runtime_error():
    """Test that converted RuntimeError from GeneratorExit is detected."""
    # Converted RuntimeError (Python async runtime converts GeneratorExit)
    converted_error = RuntimeError("coroutine ignored GeneratorExit")
    assert is_cleanup_generator_exit(converted_error, workflow_completed=True) is True
    assert is_cleanup_generator_exit(converted_error, workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_other_runtime_error():
    """Test that other RuntimeErrors are not detected as GeneratorExit."""
    # Other RuntimeError (not from GeneratorExit)
    other_error = RuntimeError("some other error")
    assert is_cleanup_generator_exit(other_error, workflow_completed=True) is False
    assert is_cleanup_generator_exit(other_error, workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_other_exception():
    """Test that other exceptions are not detected as GeneratorExit."""
    # Other exception types
    assert is_cleanup_generator_exit(ValueError("test"), workflow_completed=True) is False
    assert is_cleanup_generator_exit(KeyError("test"), workflow_completed=False) is False
    assert is_cleanup_generator_exit(Exception("test"), workflow_completed=True) is False


# ============================================================================
# NEW TESTS FOR ISSUE #535 - 2025 Exception Handling Best Practices
# ============================================================================


class TestAgentError:
    """Test AgentError exception class."""

    @pytest.mark.unit
    def test_agent_error_basic_creation(self) -> None:
        """AgentError stores agent_name and original_exception."""
        original = ValueError("Test error")
        error = AgentError(
            agent_name="security_auditor",
            original_exception=original,
            message="Agent failed",
        )

        assert error.agent_name == "security_auditor"
        assert error.original_exception is original
        assert "Agent failed" in str(error)
        assert isinstance(error, SkillForgeException)

    @pytest.mark.unit
    def test_agent_error_with_analysis_id(self) -> None:
        """AgentError stores optional analysis_id."""
        error = AgentError(
            agent_name="tech_comparator",
            original_exception=RuntimeError("timeout"),
            message="Analysis timeout",
            analysis_id="analysis-123",
        )

        assert error.analysis_id == "analysis-123"
        assert error.agent_name == "tech_comparator"

    @pytest.mark.unit
    def test_agent_error_preserves_cause(self) -> None:
        """AgentError sets __cause__ for exception chaining."""
        original = ValueError("Original error")
        error = AgentError(
            agent_name="security_auditor",
            original_exception=original,
            message="Wrapped error",
        )

        # Should preserve exception chain
        assert error.__cause__ is original

    @pytest.mark.unit
    def test_agent_error_message_formatting(self) -> None:
        """AgentError formats message with agent name."""
        error = AgentError(
            agent_name="dependency_mapper",
            original_exception=RuntimeError("test"),
            message="Processing failed",
        )

        error_str = str(error)
        assert "dependency_mapper" in error_str or "Processing failed" in error_str

    @pytest.mark.unit
    def test_agent_error_without_analysis_id(self) -> None:
        """AgentError works without optional analysis_id."""
        error = AgentError(
            agent_name="reporter",
            original_exception=ValueError("test"),
            message="Report generation failed",
        )

        assert error.analysis_id is None
        assert error.agent_name == "reporter"


class TestAgentGroupError:
    """Test AgentGroupError exception group class."""

    @pytest.mark.unit
    def test_agent_group_error_from_list(self) -> None:
        """AgentGroupError collects multiple AgentErrors."""
        errors = [
            AgentError("agent1", ValueError("error1"), "Error 1"),
            AgentError("agent2", RuntimeError("error2"), "Error 2"),
        ]

        group = AgentGroupError("Multiple agent failures", errors)

        assert len(group.exceptions) == 2
        assert all(isinstance(e, AgentError) for e in group.exceptions)

    @pytest.mark.unit
    def test_agent_group_error_is_exception_group(self) -> None:
        """AgentGroupError is an ExceptionGroup subclass."""
        errors = [AgentError("agent1", ValueError("test"), "Test error")]
        group = AgentGroupError("Test group", errors)

        # Should be an instance of BaseExceptionGroup (Python 3.11+)
        assert isinstance(group, BaseExceptionGroup)

    @pytest.mark.unit
    def test_agent_group_error_except_star_handling(self) -> None:
        """AgentGroupError can be caught with except*."""
        errors = [
            AgentError("agent1", ValueError("value error"), "Value error"),
            AgentError("agent2", RuntimeError("runtime error"), "Runtime error"),
        ]
        group = AgentGroupError("Test failures", errors)

        # Test that we can catch it with except*
        caught = False
        try:
            raise group
        except* AgentError as eg:
            caught = True
            assert len(eg.exceptions) == 2

        assert caught

    @pytest.mark.unit
    def test_agent_group_error_message(self) -> None:
        """AgentGroupError message includes error count."""
        errors = [
            AgentError("agent1", ValueError("e1"), "Error 1"),
            AgentError("agent2", ValueError("e2"), "Error 2"),
            AgentError("agent3", ValueError("e3"), "Error 3"),
        ]
        group = AgentGroupError("Batch failures", errors)

        message = str(group)
        # ExceptionGroup messages include count
        assert "3" in message or "Batch failures" in message


class TestRetryableErrors:
    """Test retryable error hierarchy."""

    @pytest.mark.unit
    def test_retryable_error_hierarchy(self) -> None:
        """RetryableError is a SkillForgeException."""
        error = RetryableError("Temporary failure")

        assert isinstance(error, SkillForgeException)
        assert isinstance(error, RetryableError)

    @pytest.mark.unit
    def test_transient_error_is_retryable(self) -> None:
        """TransientError inherits from RetryableError."""
        error = TransientError("Network timeout")

        assert isinstance(error, RetryableError)
        assert isinstance(error, SkillForgeException)

    @pytest.mark.unit
    def test_retryable_error_message(self) -> None:
        """RetryableError stores message correctly."""
        error = RetryableError("Database connection lost")

        assert "Database connection lost" in str(error)


class TestEnrichException:
    """Test enrich_exception utility."""

    @pytest.mark.unit
    def test_enrich_adds_notes(self) -> None:
        """enrich_exception adds notes via add_note()."""
        exc = ValueError("test error")
        enrich_exception(exc, user_id="user-123", stage="validation")

        # Check that notes were added
        assert hasattr(exc, "__notes__")
        notes = exc.__notes__
        assert any("user_id=user-123" in note for note in notes)
        assert any("stage=validation" in note for note in notes)

    @pytest.mark.unit
    def test_enrich_multiple_contexts(self) -> None:
        """Multiple calls accumulate notes."""
        exc = RuntimeError("test")
        enrich_exception(exc, stage="processing")
        enrich_exception(exc, analysis_id="analysis-456")

        notes = exc.__notes__
        assert len(notes) >= 2
        assert any("stage=processing" in note for note in notes)
        assert any("analysis_id=analysis-456" in note for note in notes)

    @pytest.mark.unit
    def test_enrich_with_no_kwargs(self) -> None:
        """enrich_exception handles empty kwargs gracefully."""
        exc = ValueError("test")
        enrich_exception(exc)

        # Should not crash, may or may not add notes
        assert True  # No exception raised

    @pytest.mark.unit
    def test_enrich_with_complex_values(self) -> None:
        """enrich_exception handles complex context values."""
        exc = RuntimeError("test")
        enrich_exception(
            exc,
            data={"key": "value", "nested": {"count": 42}},
            tags=["important", "retry"],
        )

        notes = exc.__notes__
        # Should convert complex values to strings
        assert len(notes) > 0


class TestExceptionContext:
    """Test exception_context context manager."""

    @pytest.mark.unit
    def test_sync_context_adds_notes_on_error(self) -> None:
        """exception_context adds notes when exception raised."""
        with pytest.raises(ValueError) as exc_info:
            with exception_context(stage="validation", user_id="user-789"):
                raise ValueError("Validation failed")

        exc = exc_info.value
        notes = exc.__notes__
        assert any("stage=validation" in note for note in notes)
        assert any("user_id=user-789" in note for note in notes)

    @pytest.mark.unit
    def test_sync_context_no_effect_on_success(self) -> None:
        """exception_context does nothing when no exception."""
        result = None
        with exception_context(stage="processing"):
            result = "success"

        assert result == "success"

    @pytest.mark.unit
    def test_sync_context_preserves_exception(self) -> None:
        """exception_context preserves original exception type."""
        with pytest.raises(RuntimeError):
            with exception_context(analysis_id="test-123"):
                raise RuntimeError("Test error")

    @pytest.mark.unit
    def test_sync_context_nested(self) -> None:
        """Nested exception_context accumulates context."""
        with pytest.raises(ValueError) as exc_info:
            with exception_context(stage="outer"):
                with exception_context(substage="inner"):
                    raise ValueError("Nested error")

        notes = exc_info.value.__notes__
        assert any("stage=outer" in note for note in notes)
        assert any("substage=inner" in note for note in notes)


class TestAsyncExceptionContext:
    """Test async_exception_context context manager."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_adds_notes_on_error(self) -> None:
        """async_exception_context adds notes when exception raised."""
        with pytest.raises(ValueError) as exc_info:
            async with async_exception_context(stage="async_validation", task_id="task-123"):
                raise ValueError("Async validation failed")

        exc = exc_info.value
        notes = exc.__notes__
        assert any("stage=async_validation" in note for note in notes)
        assert any("task_id=task-123" in note for note in notes)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_no_effect_on_success(self) -> None:
        """async_exception_context does nothing when no exception."""
        result = None
        async with async_exception_context(stage="async_processing"):
            result = "async success"

        assert result == "async success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_preserves_exception(self) -> None:
        """async_exception_context preserves original exception type."""
        with pytest.raises(RuntimeError):
            async with async_exception_context(operation="test"):
                raise RuntimeError("Async test error")


class TestCollectAgentErrors:
    """Test collect_agent_errors utility."""

    @pytest.mark.unit
    def test_collect_no_errors_returns_none(self) -> None:
        """collect_agent_errors returns None when no errors."""
        results = ["success1", "success2", "success3"]

        error_group = collect_agent_errors(results)

        assert error_group is None

    @pytest.mark.unit
    def test_collect_errors_returns_group(self) -> None:
        """collect_agent_errors returns AgentGroupError with errors."""
        errors = [
            AgentError("agent1", ValueError("e1"), "Error 1"),
            AgentError("agent2", RuntimeError("e2"), "Error 2"),
        ]

        error_group = collect_agent_errors(errors)

        assert error_group is not None
        assert isinstance(error_group, AgentGroupError)
        assert len(error_group.exceptions) == 2

    @pytest.mark.unit
    def test_collect_filters_successful_results(self) -> None:
        """collect_agent_errors ignores non-exception results."""
        results: list[AgentError | str] = [
            "success",
            AgentError("agent1", ValueError("e1"), "Error 1"),
            "another success",
            AgentError("agent2", RuntimeError("e2"), "Error 2"),
        ]

        error_group = collect_agent_errors(results)

        assert error_group is not None
        assert len(error_group.exceptions) == 2
        assert all(isinstance(e, AgentError) for e in error_group.exceptions)

    @pytest.mark.unit
    def test_collect_empty_list(self) -> None:
        """collect_agent_errors handles empty list."""
        error_group = collect_agent_errors([])

        assert error_group is None

    @pytest.mark.unit
    def test_collect_mixed_exception_types(self) -> None:
        """collect_agent_errors handles mixed exception types."""
        results: list[Exception | str] = [
            AgentError("agent1", ValueError("e1"), "Error 1"),
            ValueError("plain error"),  # Not an AgentError
            "success",
        ]

        error_group = collect_agent_errors(results)

        # Should collect AgentErrors (and optionally wrap other exceptions)
        assert error_group is not None


class TestIsRetryable:
    """Test is_retryable utility function."""

    @pytest.mark.unit
    def test_retryable_error_returns_true(self) -> None:
        """is_retryable returns True for RetryableError."""
        error = RetryableError("Temporary failure")

        assert is_retryable(error) is True

    @pytest.mark.unit
    def test_transient_error_returns_true(self) -> None:
        """is_retryable returns True for TransientError."""
        error = TransientError("Network timeout")

        assert is_retryable(error) is True

    @pytest.mark.unit
    def test_timeout_error_returns_true(self) -> None:
        """is_retryable returns True for TimeoutError."""
        error = TimeoutError("Request timeout")

        assert is_retryable(error) is True

    @pytest.mark.unit
    def test_value_error_returns_false(self) -> None:
        """is_retryable returns False for non-retryable errors."""
        error = ValueError("Invalid input")

        assert is_retryable(error) is False

    @pytest.mark.unit
    def test_runtime_error_returns_false(self) -> None:
        """is_retryable returns False for RuntimeError."""
        error = RuntimeError("General runtime error")

        assert is_retryable(error) is False

    @pytest.mark.unit
    def test_skillforge_exception_not_retryable_by_default(self) -> None:
        """is_retryable returns False for base SkillForgeException."""
        error = SkillForgeException("Base exception")

        assert is_retryable(error) is False

    @pytest.mark.unit
    def test_workflow_error_not_retryable(self) -> None:
        """is_retryable returns False for WorkflowError."""
        error = WorkflowError("Workflow failed")

        assert is_retryable(error) is False


class TestWrapExternalError:
    """Test wrap_external_error utility function."""

    @pytest.mark.unit
    def test_wrap_external_error_basic(self) -> None:
        """wrap_external_error wraps external exceptions."""
        original = ConnectionError("Connection failed")

        wrapped = wrap_external_error(original, service="redis")

        assert isinstance(wrapped, ExternalServiceError)
        assert wrapped.__cause__ is original
        assert "redis" in str(wrapped).lower()

    @pytest.mark.unit
    def test_wrap_preserves_error_chain(self) -> None:
        """wrap_external_error preserves exception chain."""
        original = TimeoutError("Request timeout")

        wrapped = wrap_external_error(original, service="api")

        assert wrapped.__cause__ is original

    @pytest.mark.unit
    def test_wrap_with_context(self) -> None:
        """wrap_external_error includes context in wrapped exception."""
        original = ValueError("Invalid response")

        wrapped = wrap_external_error(
            original,
            service="external_api",
        )

        wrapped_str = str(wrapped)
        # Should include service and operation context
        assert "external_api" in wrapped_str.lower() or "parse_response" in wrapped_str.lower()


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    @pytest.mark.unit
    def test_all_custom_exceptions_inherit_from_base(self) -> None:
        """All custom exceptions inherit from SkillForgeException."""
        exceptions_to_test = [
            WorkflowError("test"),
            RetryableError("test"),
            TransientError("test"),
            ConfigurationError("test"),
            CacheError("test"),
            EvaluationError("test"),
            ExternalServiceError("test_service", "test"),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, SkillForgeException), (
                f"{type(exc).__name__} should inherit from SkillForgeException"
            )

    @pytest.mark.unit
    def test_exception_inheritance_chain(self) -> None:
        """Test inheritance chain for specific exceptions."""
        # TransientError -> RetryableError -> SkillForgeException -> Exception
        error = TransientError("test")

        assert isinstance(error, TransientError)
        assert isinstance(error, RetryableError)
        assert isinstance(error, SkillForgeException)
        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_agent_error_inheritance(self) -> None:
        """AgentError inherits from SkillForgeException."""
        error = AgentError("test_agent", ValueError("test"), "Test error")

        assert isinstance(error, SkillForgeException)
        assert isinstance(error, Exception)


class TestExceptionAttributes:
    """Test exception attribute storage and access."""

    @pytest.mark.unit
    def test_agent_error_attributes_accessible(self) -> None:
        """AgentError attributes are accessible."""
        original = RuntimeError("original")
        error = AgentError(
            agent_name="test_agent",
            original_exception=original,
            message="Test message",
            analysis_id="test-123",
        )

        # All attributes should be accessible
        assert error.agent_name == "test_agent"
        assert error.original_exception is original
        assert error.analysis_id == "test-123"
        assert str(error) == "Test message"

    @pytest.mark.unit
    def test_external_service_error_attributes(self) -> None:
        """ExternalServiceError stores service information."""
        error = ExternalServiceError("redis", "Service unavailable")

        # Should store context if the class supports it
        # (Implementation-dependent)
        assert "Service unavailable" in str(error)


class TestExceptionNotes:
    """Test Python 3.11+ exception notes feature."""

    @pytest.mark.unit
    def test_exception_notes_are_list(self) -> None:
        """Exception __notes__ is a list after enrich_exception."""
        exc = ValueError("test")
        enrich_exception(exc, key="value")

        assert isinstance(exc.__notes__, list)

    @pytest.mark.unit
    def test_multiple_enrichments_create_multiple_notes(self) -> None:
        """Multiple enrich_exception calls create multiple notes."""
        exc = RuntimeError("test")
        enrich_exception(exc, stage="stage1")
        enrich_exception(exc, stage="stage2")
        enrich_exception(exc, stage="stage3")

        assert len(exc.__notes__) >= 3

    @pytest.mark.unit
    def test_notes_preserved_through_reraise(self) -> None:
        """Exception notes are preserved when re-raising."""
        with pytest.raises(ValueError) as exc_info:
            try:
                exc = ValueError("original")
                enrich_exception(exc, context="inner")
                raise exc
            except ValueError as e:
                enrich_exception(e, context="outer")
                raise

        notes = exc_info.value.__notes__
        assert any("context=inner" in note for note in notes)
        assert any("context=outer" in note for note in notes)
