"""Standard error codes for analysis workflow stages.

These error codes are used to classify failures at different stages of the
analysis workflow for debugging, monitoring, and user feedback.
"""


class AgentStatus:
    """Agent execution status constants."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# Agent-specific error codes (detailed failure reasons)
AGENT_NO_CONTENT = "AGENT_NO_CONTENT"  # No content available for analysis
AGENT_NO_CODE = "AGENT_NO_CODE"  # Content has no code to analyze
AGENT_TIMEOUT = "AGENT_TIMEOUT"  # Agent execution timed out
AGENT_LLM_ERROR = "AGENT_LLM_ERROR"  # LLM API failure
AGENT_PARSE_ERROR = "AGENT_PARSE_ERROR"  # Output parsing failed
AGENT_SKIPPED_ABORT = "AGENT_SKIPPED_ABORT"  # Workflow is aborting
AGENT_LOW_SPECIFICITY = "AGENT_LOW_SPECIFICITY"  # Below quality threshold
AGENT_CANCELLED = "AGENT_CANCELLED"  # GeneratorExit or cancellation

# Agent errors
SECURITY_AUDITOR_FAILED = "SECURITY_AUDITOR_FAILED"
TECH_COMPARATOR_FAILED = "TECH_COMPARATOR_FAILED"
PERFORMANCE_ANALYST_FAILED = "PERFORMANCE_ANALYST_FAILED"
DEPENDENCY_MAPPER_FAILED = "DEPENDENCY_MAPPER_FAILED"
IMPLEMENTATION_PLANNER_FAILED = "IMPLEMENTATION_PLANNER_FAILED"
CODE_QUALITY_CRITIC_FAILED = "CODE_QUALITY_CRITIC_FAILED"
INTEGRATION_FEASIBILITY_FAILED = "INTEGRATION_FEASIBILITY_FAILED"
TREND_VALIDATOR_FAILED = "TREND_VALIDATOR_FAILED"

# Workflow stage errors
EXTRACTION_FAILED = "EXTRACTION_FAILED"
SUPERVISOR_FAILED = "SUPERVISOR_FAILED"
AGGREGATION_FAILED = "AGGREGATION_FAILED"
QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"
COMPRESSION_FAILED = "COMPRESSION_FAILED"
ARTIFACT_GENERATION_FAILED = "ARTIFACT_GENERATION_FAILED"
EMBEDDING_FAILED = "EMBEDDING_FAILED"

# Agent type to error code mapping
AGENT_ERROR_CODES: dict[str, str] = {
    "security_auditor": SECURITY_AUDITOR_FAILED,
    "tech_comparator": TECH_COMPARATOR_FAILED,
    "performance_analyst": PERFORMANCE_ANALYST_FAILED,
    "dependency_mapper": DEPENDENCY_MAPPER_FAILED,
    "implementation_planner": IMPLEMENTATION_PLANNER_FAILED,
    "code_quality_critic": CODE_QUALITY_CRITIC_FAILED,
    "integration_feasibility": INTEGRATION_FEASIBILITY_FAILED,
    "trend_validator": TREND_VALIDATOR_FAILED,
}
