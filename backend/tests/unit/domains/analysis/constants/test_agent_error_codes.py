"""Unit tests for agent error codes and status constants.

Validates the error code constants defined in error_codes.py to ensure:
1. New constants like AGENT_BULKHEAD_REJECTED exist
2. All constants are strings (no None values)
3. AgentStatus constants are valid strings
"""

from app.domains.analysis.constants.error_codes import (
    ACTIONABLE_FAILED,
    AGENT_BULKHEAD_REJECTED,
    AGENT_CANCELLED,
    AGENT_ERROR_CODES,
    AGENT_LLM_ERROR,
    AGENT_LOW_SPECIFICITY,
    AGENT_NO_CODE,
    AGENT_NO_CONTENT,
    AGENT_PARSE_ERROR,
    AGENT_SKIPPED_ABORT,
    AGENT_TIMEOUT,
    CODE_QUALITY_CRITIC_FAILED,
    DEPENDENCY_MAPPER_FAILED,
    IMPLEMENTATION_PLANNER_FAILED,
    INTEGRATION_FEASIBILITY_FAILED,
    PERFORMANCE_ANALYST_FAILED,
    SECURITY_AUDITOR_FAILED,
    TECH_COMPARATOR_FAILED,
    TREND_VALIDATOR_FAILED,
    AgentStatus,
)


def test_agent_bulkhead_rejected_constant_exists():
    """Test that AGENT_BULKHEAD_REJECTED constant exists and has correct value.

    This validates the new constant added for Issue #588 (bulkhead pattern).
    """
    assert AGENT_BULKHEAD_REJECTED == "AGENT_BULKHEAD_REJECTED"
    assert isinstance(AGENT_BULKHEAD_REJECTED, str)
    assert len(AGENT_BULKHEAD_REJECTED) > 0


def test_all_agent_status_constants_are_strings():
    """Test that all AgentStatus constants are valid non-empty strings."""
    status_values = [
        AgentStatus.SUCCESS,
        AgentStatus.FAILED,
        AgentStatus.SKIPPED,
    ]

    for status in status_values:
        assert isinstance(status, str), f"AgentStatus value {status} is not a string"
        assert status is not None, "AgentStatus value is None"
        assert len(status) > 0, "AgentStatus value is empty string"


def test_all_agent_error_codes_are_strings():
    """Test that all AGENT_* error codes are valid non-empty strings."""
    agent_error_codes = [
        AGENT_NO_CONTENT,
        AGENT_NO_CODE,
        AGENT_TIMEOUT,
        AGENT_LLM_ERROR,
        AGENT_PARSE_ERROR,
        AGENT_SKIPPED_ABORT,
        AGENT_LOW_SPECIFICITY,
        AGENT_CANCELLED,
        AGENT_BULKHEAD_REJECTED,
    ]

    for error_code in agent_error_codes:
        assert isinstance(error_code, str), f"Agent error code {error_code} is not a string"
        assert error_code is not None, "Agent error code is None"
        assert len(error_code) > 0, "Agent error code is empty string"


def test_all_agent_specific_failure_codes_are_strings():
    """Test that all agent-specific failure codes are valid non-empty strings."""
    agent_failure_codes = [
        ACTIONABLE_FAILED,
        SECURITY_AUDITOR_FAILED,
        TECH_COMPARATOR_FAILED,
        PERFORMANCE_ANALYST_FAILED,
        DEPENDENCY_MAPPER_FAILED,
        IMPLEMENTATION_PLANNER_FAILED,
        CODE_QUALITY_CRITIC_FAILED,
        INTEGRATION_FEASIBILITY_FAILED,
        TREND_VALIDATOR_FAILED,
    ]

    for error_code in agent_failure_codes:
        assert isinstance(error_code, str), f"Agent failure code {error_code} is not a string"
        assert error_code is not None, "Agent failure code is None"
        assert len(error_code) > 0, "Agent failure code is empty string"


def test_agent_error_codes_mapping_is_valid():
    """Test that AGENT_ERROR_CODES mapping contains valid string values."""
    assert isinstance(AGENT_ERROR_CODES, dict), "AGENT_ERROR_CODES is not a dict"
    assert len(AGENT_ERROR_CODES) > 0, "AGENT_ERROR_CODES is empty"

    for agent_type, error_code in AGENT_ERROR_CODES.items():
        assert isinstance(agent_type, str), f"Agent type key {agent_type} is not a string"
        assert isinstance(error_code, str), f"Error code value {error_code} is not a string"
        assert error_code is not None, f"Error code for {agent_type} is None"
        assert len(error_code) > 0, f"Error code for {agent_type} is empty string"


def test_agent_status_values_are_lowercase():
    """Test that AgentStatus values follow lowercase convention."""
    assert AgentStatus.SUCCESS == "success", "AgentStatus.SUCCESS should be lowercase 'success'"
    assert AgentStatus.FAILED == "failed", "AgentStatus.FAILED should be lowercase 'failed'"
    assert AgentStatus.SKIPPED == "skipped", "AgentStatus.SKIPPED should be lowercase 'skipped'"


def test_agent_error_codes_are_uppercase():
    """Test that AGENT_* error codes follow UPPER_SNAKE_CASE convention."""
    agent_error_codes = [
        ("AGENT_NO_CONTENT", AGENT_NO_CONTENT),
        ("AGENT_NO_CODE", AGENT_NO_CODE),
        ("AGENT_TIMEOUT", AGENT_TIMEOUT),
        ("AGENT_LLM_ERROR", AGENT_LLM_ERROR),
        ("AGENT_PARSE_ERROR", AGENT_PARSE_ERROR),
        ("AGENT_SKIPPED_ABORT", AGENT_SKIPPED_ABORT),
        ("AGENT_LOW_SPECIFICITY", AGENT_LOW_SPECIFICITY),
        ("AGENT_CANCELLED", AGENT_CANCELLED),
        ("AGENT_BULKHEAD_REJECTED", AGENT_BULKHEAD_REJECTED),
    ]

    for expected_name, actual_value in agent_error_codes:
        assert actual_value == expected_name, (
            f"Error code should match variable name: {expected_name}"
        )
        assert actual_value.isupper() or "_" in actual_value, (
            f"Error code should be UPPER_SNAKE_CASE: {actual_value}"
        )


def test_agent_error_codes_mapping_completeness():
    """Test that AGENT_ERROR_CODES mapping includes all expected agent types."""
    expected_agent_types = [
        "actionable",
        "security_auditor",
        "tech_comparator",
        "performance_analyst",
        "dependency_mapper",
        "implementation_planner",
        "code_quality_critic",
        "integration_feasibility",
        "trend_validator",
    ]

    for agent_type in expected_agent_types:
        assert agent_type in AGENT_ERROR_CODES, (
            f"Agent type '{agent_type}' missing from AGENT_ERROR_CODES mapping"
        )


def test_no_duplicate_error_code_values():
    """Test that all error codes have unique values (no duplicates)."""
    all_error_codes = [
        AGENT_NO_CONTENT,
        AGENT_NO_CODE,
        AGENT_TIMEOUT,
        AGENT_LLM_ERROR,
        AGENT_PARSE_ERROR,
        AGENT_SKIPPED_ABORT,
        AGENT_LOW_SPECIFICITY,
        AGENT_CANCELLED,
        AGENT_BULKHEAD_REJECTED,
        ACTIONABLE_FAILED,
        SECURITY_AUDITOR_FAILED,
        TECH_COMPARATOR_FAILED,
        PERFORMANCE_ANALYST_FAILED,
        DEPENDENCY_MAPPER_FAILED,
        IMPLEMENTATION_PLANNER_FAILED,
        CODE_QUALITY_CRITIC_FAILED,
        INTEGRATION_FEASIBILITY_FAILED,
        TREND_VALIDATOR_FAILED,
    ]

    unique_codes = set(all_error_codes)
    assert len(unique_codes) == len(all_error_codes), "Duplicate error code values detected"
