"""Security Auditor Agent for security risk analysis.

This agent identifies security risks, vulnerabilities, and best practices
in the analyzed content, focusing on OWASP Top 10, authentication, data exposure,
and compliance considerations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas.security_auditor import SecurityAudit

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

Be thorough and prioritize critical vulnerabilities."""


async def run_security_auditor(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run security auditor agent to identify security risks and vulnerabilities.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=SECURITY_AUDITOR_PROMPT,
        response_schema=SecurityAudit,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="security_auditor",
        session=session,
    )
