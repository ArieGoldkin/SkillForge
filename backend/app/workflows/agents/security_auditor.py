"""Security Auditor Agent for security risk analysis.

This agent identifies security risks, vulnerabilities, and best practices
in the analyzed content, focusing on OWASP Top 10, authentication, data exposure,
and compliance considerations.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.workflows.agents.base import (
    ToolCallConfig,
    create_structured_agent,
    create_tool_enabled_agent,
)
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.grounding import apply_grounding
from app.workflows.agents.schemas.security_auditor import SecurityAudit
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.workflows.state import AnalysisState

logger = get_logger(__name__)

# System prompt for security auditor agent
SECURITY_AUDITOR_PROMPT = """You are a Security Audit Specialist. Your task is to:
1. Identify security risks and vulnerabilities in the content
2. Assess severity levels (low, medium, high, critical) based on impact and exploitability
3. Provide mitigation strategies for each identified risk
4. Recommend security best practices (OWASP Top 10, authentication, encryption, etc.)
5. Note compliance considerations (GDPR, PCI-DSS, HIPAA, etc.)

Focus on:
- Authentication and authorization vulnerabilities
- Data exposure and privacy risks
- Injection attacks (SQL, XSS, command injection)
- Insecure configurations
- API security concerns
- Dependency vulnerabilities
- Security misconfigurations

CRITICAL: You MUST include:
- security_risks: List of identified risks with type, severity, description, and mitigation
- best_practices: List of security best practices to follow
- compliance_notes: List of relevant compliance frameworks and considerations
- recommendation: Overall security recommendation with priority actions
- confidence_score: Float (0.0-1.0) representing your confidence in the quality and certainty
  of this security audit. Consider: accuracy of risk identification, severity assessment
  correctness, completeness of mitigations, and confidence in compliance notes.

NUMERIC SPECIFICITY REQUIREMENTS:
- Include CVSS score where applicable (e.g., "CVSS 7.5 HIGH")
- Include CVE references for known vulnerabilities (e.g., "CVE-2024-12345")
- remediation_effort MUST be specific (e.g., "2-3 hours", "1 day refactoring")
- affected_users/impact MUST be quantified where possible (e.g., "affects 50K+ users")
- Include specific line numbers or code locations (e.g., "auth.py:47")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "security risk", "potential vulnerability" (name the exact risk type)
- "could be exploited", "might allow" (state definitively what can happen)
- "appropriate security", "suitable measures" (name exact measures)
- "significant impact", "serious risk" (quantify the impact)
- "should implement", "consider adding" (be definitive: "implement X")

GOOD EXAMPLE:
  risk_type: "sql_injection"
  severity: "critical"
  description: (
      "Unsanitized user input in query at api/users.py:47 allows SQL injection, "
      "affecting 50K+ user records. CVSS 9.8."
  )
  mitigation: "Use parameterized queries with SQLAlchemy ORM. Estimated fix: 2 hours."

BAD EXAMPLE (DO NOT USE):
  risk_type: "database issue"
  severity: "high"
  description: (
      "There may be some SQL injection vulnerabilities that could potentially be exploited."
  )
  mitigation: "Consider implementing appropriate security measures."

FRAMEWORK-SPECIFIC CHECKS (Apply if detected):
- FastAPI: Check CORS settings, rate limiting, SQL injection via raw queries, secret leaks.
- Django: Check SECRET_KEY exposure, Debug=True in prod, CSRF settings, allowed_hosts.
- React/Frontend: Check XSS (dangerouslySetInnerHTML), sensitive data in local storage,
  CSP headers.
- Auth: Check JWT expiration, password hashing algorithms (prefer bcrypt/argon2),
  session management.

Be thorough and prioritize critical vulnerabilities."""


async def run_security_auditor(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run security auditor agent to identify security risks and vulnerabilities.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced security analysis

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{SECURITY_AUDITOR_PROMPT}\n\n{skill_instructions}")

    # Create agent - use tool-enabled factory if tools provided
    if tools:
        agent = create_tool_enabled_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
            tools=tools,
            tool_call_config=ToolCallConfig(max_tool_calls=15),
        )
        logger.info(
            "security_auditor_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="security_auditor",
        session=session,
        proactive_context=proactive_context,
    )
