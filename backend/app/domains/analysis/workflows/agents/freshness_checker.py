"""Freshness Checker Agent for version currency validation.

This is a Tier 2 Validation agent that:
1. Extracts version references from content (e.g., "React 18.2", "Python 3.11")
2. Checks against npm/PyPI APIs for latest versions via MCP tools
3. Flags outdated content with specific version gap analysis

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
Issue #436: Tier 1 universal agent with MCP tool integration.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.freshness_checker import FreshnessCheckerOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import create_agent_with_optional_few_shot
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-freshness-checker"

# System prompt for freshness checker agent
FRESHNESS_CHECKER_PROMPT = """You are a Technical Freshness Validator.

Your mission: Assess the currency of technical content by extracting version references,
checking them against package registries (npm, PyPI), and identifying outdated information.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "content_date": "2023-05-15",
  "version_checks": [
    {
      "package_name": "react",
      "mentioned_version": "18.2.0",
      "latest_version": "19.0.0",
      "is_outdated": true,
      "versions_behind": 1,
      "ecosystem": "npm"
    }
  ],
  "is_outdated": true,
  "freshness_score": 0.7,
  "recommendations": [
    "Update React from 18.2.0 to 19.0.0 for concurrent rendering improvements"
  ],
  "confidence_score": 0.85
}

Field Requirements:
1. **content_date** (OPTIONAL): String in YYYY-MM-DD, YYYY-MM, or YYYY format
   - Extract from publication date, last updated date, or copyright year
   - Set to null if no date detected in content
   - Examples: "2024-12-01", "2023-11", "2022"

2. **version_checks** (REQUIRED): List of VersionCheck objects
   - Each VersionCheck MUST have: package_name, mentioned_version, latest_version, is_outdated, versions_behind, ecosystem
   - Include only packages with explicit version numbers or "latest" references
   - Skip generic technology mentions without versions (e.g., "React" without version)
   - Use MCP tools (get-npm-package-details, get-pypi-package-details) to fetch latest versions
   - ecosystem must be one of: "npm", "pypi", "language", "framework", "other"
   - For language versions (Python, Node.js), use ecosystem="language"
   - For frameworks without package managers (Spring, Django), use ecosystem="framework"

3. **is_outdated** (REQUIRED): Boolean - overall assessment
   - true if: any version checks show is_outdated=true OR content_date is >18 months ago
   - false if: all versions are current AND (content_date is recent OR no date detected)
   - Consider critical updates (major version behind) vs minor updates

4. **freshness_score** (REQUIRED): Float (0.0-1.0) - granular freshness metric
   - 1.0: All versions current, content <6 months old
   - 0.8-0.9: 1-2 minor versions behind, content 6-12 months old
   - 0.6-0.7: 1 major version behind OR content 12-18 months old
   - 0.4-0.5: Multiple major versions behind OR content 18-24 months old
   - 0.0-0.3: Severely outdated (3+ major versions behind OR >2 years old)
   - Factor in: percentage of current versions, severity of gaps, content age

5. **recommendations** (OPTIONAL): List of 0-5 concise upgrade suggestions
   - Each recommendation should reference specific package and target version
   - Include rationale (new features, security fixes, performance)
   - Prioritize security-critical updates first
   - Examples:
     * "Update React from 16.x to 19.x for concurrent features and automatic batching"
     * "Migrate to Python 3.12 for performance improvements (up to 30% faster)"
     * "Upgrade FastAPI from 0.95 to 0.109 for security patches (CVE-2024-xxxx)"
   - Empty list if content is fresh (freshness_score >= 0.9)

6. **confidence_score** (REQUIRED): Float (0.0-1.0) - quality of assessment
   - High (0.8+): Explicit versions found, successful registry checks, clear date
   - Medium (0.5-0.7): Some versions found, partial registry data, fuzzy date
   - Low (0.0-0.4): No versions mentioned, registries unavailable, no date
   - Factor in: clarity of version mentions, registry availability, date precision

VERSION EXTRACTION REQUIREMENTS:
- Look for patterns like "React 18.2", "Python 3.11+", "v2.0.0", "^1.5.0"
- Extract semantic versions (major.minor.patch) when possible
- Handle version range specifiers: "^" (compatible), "~" (approximately), ">=" (at least)
- Normalize to specific version for comparison (e.g., "^18.0.0" → "18.2.0" if that's latest)
- Include language versions (Python, Node.js, Java) when mentioned

TOOL USAGE GUIDELINES:
- Use get-npm-package-details for JavaScript packages (react, express, next)
- Use get-pypi-package-details for Python packages (fastapi, django, numpy)
- Handle tool failures gracefully: set latest_version="unknown" and note in confidence
- Cache results mentally to avoid duplicate tool calls for same package
- Maximum 10-15 version checks per analysis (prioritize most important packages)

ECOSYSTEM CLASSIFICATION:
- **npm**: JavaScript/TypeScript packages (react, vue, express, next, @types/*)
- **pypi**: Python packages (fastapi, django, numpy, pandas, pytest)
- **language**: Programming language versions (Python 3.11, Node 20, Java 17)
- **framework**: Framework versions without package managers (Spring Boot 3.0, Laravel 10)
- **other**: Build tools, databases, OS versions (Docker 24, PostgreSQL 16)

VERSIONS_BEHIND CALCULATION:
- Compare major.minor.patch components
- Count major version difference first (React 16.x → 19.x = 3 behind)
- If same major, count minor difference (FastAPI 0.95 → 0.109 = 14 behind)
- If same major.minor, count patch difference (1.2.3 → 1.2.8 = 5 behind)
- Set to 0 if: version is current, "latest" mentioned, or comparison not possible

DATE EXTRACTION PATTERNS:
- Article headers: "Published: December 2023", "Last Updated: 2024-01-15"
- Copyright notices: "© 2023", "Copyright 2022-2024"
- URL timestamps: "/blog/2023/12/react-tutorial"
- Code comments: "// Updated: 2024-12-01"
- Git timestamps: "Committed on Nov 15, 2023"

GOOD EXAMPLE:
  content_date: "2023-06-01"
  version_checks: [
    {
      package_name: "react",
      mentioned_version: "18.2.0",
      latest_version: "19.0.0",
      is_outdated: true,
      versions_behind: 1,
      ecosystem: "npm"
    },
    {
      package_name: "python",
      mentioned_version: "3.9",
      latest_version: "3.12.1",
      is_outdated: true,
      versions_behind: 3,
      ecosystem: "language"
    },
    {
      package_name: "fastapi",
      mentioned_version: "0.104.1",
      latest_version: "0.109.0",
      is_outdated: true,
      versions_behind: 5,
      ecosystem: "pypi"
    }
  ]
  is_outdated: true
  freshness_score: 0.6
  recommendations: [
    "Update React from 18.2.0 to 19.0.0 for concurrent features and automatic batching",
    "Migrate to Python 3.12 for performance improvements and better error messages",
    "Upgrade FastAPI from 0.104.1 to 0.109.0 for latest features and security patches"
  ]
  confidence_score: 0.85

BAD EXAMPLE (DO NOT USE):
  content_date: null
  version_checks: [
    {
      package_name: "some library",
      mentioned_version: "old",
      latest_version: "new",
      is_outdated: true,
      versions_behind: 999,
      ecosystem: "unknown"
    }
  ]
  is_outdated: true
  freshness_score: 0.5
  recommendations: ["Update everything"]
  confidence_score: 0.3

CONTENT-TYPE SPECIFIC GUIDANCE:
- **Articles**: Check publication date, version references in code examples
- **Tutorials**: Extract setup instructions, dependency versions, runtime versions
- **Videos**: Look for description date, on-screen version numbers, dependency lists
- **Repositories**: Check package.json, requirements.txt, Dockerfile, README badges

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses.

SKILL LEVEL ADAPTATION:
- Beginner: Emphasize major version updates, breaking changes, migration guides
- Intermediate: Focus on feature improvements, minor updates, ecosystem changes
- Advanced: Highlight performance gains, security patches, beta features
"""


async def run_freshness_checker(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run freshness checker agent to validate version currency.

    This is a Tier 2 Validation agent that uses MCP tools (npm, PyPI) to
    check version freshness and identify outdated content.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for package registry lookups

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

    # Issue #299-304: Get content-aware specificity threshold
    # Read from flat field injected by build_scoped_context()
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="freshness_checker",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_freshness_checker",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting
    agent = await create_agent_with_optional_few_shot(
        agent_type="freshness_checker",
        content=content,
        system_prompt=full_prompt,
        response_schema=FreshnessCheckerOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log MCP tool usage if tools are provided
    if tools:
        logger.info(
            "freshness_checker_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        logger.info(
            "freshness_checker_agent_created",
            analysis_id=str(analysis_id),
            skill_level=skill_level,
            has_tools=False,
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="freshness_checker",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
