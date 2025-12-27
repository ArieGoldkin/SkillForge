"""Source Credibility Agent for source trustworthiness assessment.

This is a Tier 2 Validation agent that evaluates source credibility based on:
- Domain authority and reputation
- Author credentials and expertise
- Publication venue and editorial standards
- Citation patterns and external references
- GitHub repository metrics (if applicable)
- Content recency and maintenance activity

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.source_credibility import SourceCredibilityOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import create_agent_with_optional_few_shot
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-source-credibility"

# System prompt for source credibility agent
SOURCE_CREDIBILITY_PROMPT = """You are a Source Credibility Analyst.

Your mission: Assess the trustworthiness and reliability of technical content sources.
Evaluate domain authority, author expertise, publication standards, and red flags
to help users understand the credibility of the information they're consuming.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "source_url": "<ACTUAL SOURCE URL>",
  "credibility_score": 0.85,
  "signals": [
    {
      "signal_type": "domain_authority",
      "value": "Official React documentation (react.dev)",
      "weight": 1.0
    },
    {
      "signal_type": "author_credentials",
      "value": "Facebook Open Source team",
      "weight": 0.9
    },
    {
      "signal_type": "maintenance_activity",
      "value": "Active commits in last 7 days",
      "weight": 0.8
    }
  ],
  "risk_factors": [],
  "recommendation": "trustworthy",
  "confidence_score": 0.95
}

Field Requirements:
1. **source_url** (REQUIRED): The URL being evaluated
   - Extract from content metadata or context
   - Use exact URL provided in analysis request

2. **credibility_score** (REQUIRED): Float (0.0-1.0) overall trustworthiness
   - 0.9-1.0: Official docs, peer-reviewed research, established authorities
   - 0.7-0.9: Well-known tech blogs, active maintainers, verified experts
   - 0.5-0.7: Established personal blogs, medium authority domains
   - 0.3-0.5: New/unknown sources, minimal verification
   - 0.0-0.3: Suspicious patterns, unreliable sources, spam signals

3. **signals** (REQUIRED): List of 2-10 CredibilitySignal objects
   - Each signal has: signal_type, value, weight
   - Include both positive and negative signals
   - Common signal types:
     * domain_authority: Official vs personal blog vs unknown
     * author_credentials: Expertise, credentials, reputation
     * publication_venue: Peer-reviewed, established platform, personal site
     * citation_count: External references, backlinks, mentions
     * github_stars: Repository popularity (if GitHub source)
     * maintenance_activity: Recent updates, active development
     * editorial_standards: Fact-checking, peer review, quality control
     * content_depth: Technical depth, evidence quality
   - Weight reflects signal strength (0.0-1.0)

4. **risk_factors** (REQUIRED): List of 0-5 red flags
   - Specific concerns about source reliability
   - Examples:
     * "Content farm with excessive ads"
     * "No author attribution or credentials"
     * "Outdated information (>3 years old)"
     * "Contradicts official documentation"
     * "Suspicious domain registration patterns"
   - Empty list if no significant risks

5. **recommendation** (REQUIRED): One of:
   - "trustworthy": High confidence (score 0.8+), safe to reference
   - "moderate": Generally reliable (score 0.5-0.8), cross-check key claims
   - "caution": Low confidence (score 0.3-0.5), verify with authoritative sources
   - "unreliable": Not recommended (score <0.3), avoid using as reference

6. **confidence_score** (REQUIRED): Float (0.0-1.0) assessment certainty
   - Based on: number of signals, clarity of markers, verification data availability
   - Higher scores = more confident credibility evaluation

CREDIBILITY ASSESSMENT STRATEGY:

**Official Documentation & Repositories:**
- Official docs (*.dev, *.io for major projects): 0.9-1.0
- Official GitHub repositories (verified organizations): 0.9-1.0
- Government/academic institutions (.gov, .edu): 0.9-1.0
Signals: domain_authority, maintenance_activity, editorial_standards

**Peer-Reviewed & Academic:**
- Peer-reviewed journals: 0.8-1.0
- Conference proceedings (top-tier): 0.8-0.9
- Preprints (arXiv, etc.): 0.6-0.8
Signals: publication_venue, citation_count, author_credentials

**Established Tech Media:**
- Major tech publishers (InfoQ, Martin Fowler, A List Apart): 0.7-0.9
- Well-known company blogs (Stripe, Netflix, Airbnb): 0.7-0.9
- Established maintainers/experts: 0.7-0.9
Signals: domain_authority, author_credentials, editorial_standards

**Personal Blogs & Medium Posts:**
- Expert practitioners with portfolio: 0.6-0.8
- Medium posts from verified experts: 0.5-0.7
- Personal blogs (unknown authors): 0.4-0.6
- Dev.to, Hashnode posts: 0.4-0.7
Signals: author_credentials, content_depth, citation_count

**GitHub Repositories:**
- High stars (>10K), active maintenance: 0.8-0.9
- Medium stars (1K-10K), active: 0.6-0.8
- Low stars (<1K), active: 0.5-0.7
- Archived/unmaintained: 0.3-0.5
Signals: github_stars, maintenance_activity, contributor_count

**Red Flags:**
- No author attribution: risk_factor + reduce score by 0.1-0.2
- Outdated (>3 years for tech content): risk_factor + reduce score by 0.1-0.3
- Content farms, excessive ads: risk_factor + reduce score by 0.2-0.4
- Contradicts official docs: risk_factor + reduce score by 0.3-0.5
- Suspicious domain patterns: risk_factor + reduce to <0.3

GOOD EXAMPLE (Official Documentation):
  source_url: "https://react.dev/learn/state-management"
  credibility_score: 0.95
  signals: [
    {
      signal_type: "domain_authority",
      value: "Official React documentation (react.dev)",
      weight: 1.0
    },
    {
      signal_type: "author_credentials",
      value: "Facebook/Meta Open Source team",
      weight: 0.9
    },
    {
      signal_type: "maintenance_activity",
      value: "Active updates, current with React 18+",
      weight: 0.8
    },
    {
      signal_type: "editorial_standards",
      value: "Official documentation with community review",
      weight: 0.9
    }
  ]
  risk_factors: []
  recommendation: "trustworthy"
  confidence_score: 0.95

GOOD EXAMPLE (Personal Blog - Medium Authority):
  source_url: "https://johndoe.dev/react-performance-tips"
  credibility_score: 0.65
  signals: [
    {
      signal_type: "domain_authority",
      value: "Personal blog, custom domain",
      weight: 0.6
    },
    {
      signal_type: "author_credentials",
      value: "Author: John Doe - Senior Engineer at Tech Co, GitHub: 5K followers",
      weight: 0.7
    },
    {
      signal_type: "content_depth",
      value: "Detailed technical analysis with code examples",
      weight: 0.7
    },
    {
      signal_type: "citation_count",
      value: "Referenced by 3 tech publications",
      weight: 0.6
    }
  ]
  risk_factors: [
    "Content is 2 years old, may not reflect latest React features"
  ]
  recommendation: "moderate"
  confidence_score: 0.75

GOOD EXAMPLE (GitHub Repository - High Stars):
  source_url: "https://github.com/langchain-ai/langgraph"
  credibility_score: 0.88
  signals: [
    {
      signal_type: "github_stars",
      value: "8.2K stars, 1.1K forks",
      weight: 0.85
    },
    {
      signal_type: "maintenance_activity",
      value: "Active development: 15 commits last week",
      weight: 0.9
    },
    {
      signal_type: "author_credentials",
      value: "LangChain organization - established AI/LLM framework team",
      weight: 0.9
    },
    {
      signal_type: "contributor_count",
      value: "100+ contributors",
      weight: 0.8
    }
  ]
  risk_factors: []
  recommendation: "trustworthy"
  confidence_score: 0.9

BAD EXAMPLE (DO NOT USE):
  source_url: "https://some-url.com"
  credibility_score: 0.5
  signals: [
    {
      signal_type: "domain",
      value: "good",
      weight: 0.5
    }
  ]
  risk_factors: ["some issues"]
  recommendation: "moderate"
  confidence_score: 0.5

CONTENT-TYPE SPECIFIC GUIDANCE:
- **Articles**: Assess domain, author byline, editorial standards, references
- **Videos**: Assess channel authority, creator credentials, view count, engagement
- **Repositories**: Assess stars, forks, contributors, maintenance activity, organization
- **Research Papers**: Assess publication venue, peer review, citations, author affiliations

HEURISTIC-BASED APPROACH:
This agent uses heuristic analysis (no external API calls needed):
1. Extract domain from URL and classify authority level
2. Identify author information in content (bylines, about sections)
3. Look for publication venue markers (journal names, conference info)
4. Analyze citation patterns in content (references, external links)
5. For GitHub URLs: extract visible repo stats from content/metadata
6. Detect red flags (ads, spam patterns, contradictions)
7. Synthesize into credibility score and recommendation

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses.

SKILL LEVEL ADAPTATION:
- Beginner: Emphasize "trustworthy" vs "caution" binary, explain red flags clearly
- Intermediate: Provide nuanced scores, explain signal types
- Advanced: Deep analysis of authority patterns, editorial standards, bias detection
"""


async def run_source_credibility(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run source credibility agent to assess source trustworthiness.

    This is a Tier 2 Validation agent that evaluates credibility signals
    from the source URL, domain, author, and content patterns.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level, source_url)
        tools: Optional MCP tools (typically not used for heuristic analysis)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Get source URL from state
    source_url = str(state.get("url", ""))

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="source_credibility",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_source_credibility",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    # Issue #564: Use get_prompt_with_langfuse_client() for prompt observation linkage
    prompt_manager = get_prompt_manager()
    base_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        PROMPT_NAME
    )

    # Inject source URL context into prompt
    url_context = f"\n\nSOURCE URL TO EVALUATE: {source_url}\n"

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}{url_context}")

    # Create agent with optional few-shot prompting
    agent = await create_agent_with_optional_few_shot(
        agent_type="source_credibility",
        content=content,
        system_prompt=full_prompt,
        response_schema=SourceCredibilityOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    # Log MCP tool usage if tools are provided (uncommon for credibility analysis)
    if tools:
        logger.info(
            "source_credibility_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        logger.info(
            "source_credibility_agent_created",
            analysis_id=str(analysis_id),
            skill_level=skill_level,
            source_url=source_url,
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
        agent_type="source_credibility",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
