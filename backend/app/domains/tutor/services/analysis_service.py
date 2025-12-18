"""Analysis service for tutor workflow.

Extracts analysis summary logic from repository.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_finding import AgentFinding
from app.db.models.analysis import Analysis


async def get_analysis_summary(
    session: AsyncSession,
    analysis_id: UUID,
) -> dict[str, object] | None:
    """Get analysis summary for context (from aggregated_insights).

    Args:
        session: Database session
        analysis_id: Analysis UUID

    Returns:
        Analysis summary dict or None if not found

    """
    result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        return None

    result = await session.execute(
        select(AgentFinding)
        .where(AgentFinding.analysis_id == analysis_id)
        .order_by(AgentFinding.created_at.desc())
    )
    findings = list(result.scalars().all())

    summary: dict[str, object] = {
        "title": analysis.title,
        "url": analysis.url,
        "content_type": analysis.content_type,
        "findings": [
            {"agent_type": str(f.agent_type), "findings": f.findings}  # type: ignore[attr-defined]
            for f in findings
        ],
    }

    return summary
