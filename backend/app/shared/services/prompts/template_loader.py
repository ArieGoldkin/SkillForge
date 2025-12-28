"""Jinja2 template loader for prompt templates.

Issue #414: Migrate hardcoded prompts to Jinja2 templates for:
- Template inheritance and shared macros
- Separation of concerns (prompts vs Python code)
- Easier editing and review by non-developers
- Version control friendly (clean diffs)
"""

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@lru_cache(maxsize=1)
def get_jinja_env() -> Environment:
    """Get cached Jinja2 environment configured for prompt templates.

    Returns:
        Configured Jinja2 Environment with FileSystemLoader

    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    logger.debug("jinja_env_created", templates_dir=str(TEMPLATES_DIR))
    return env


def render_template(template_path: str, **variables) -> str:
    """Render a Jinja2 template with the given variables.

    Args:
        template_path: Path to template relative to templates/ dir
        **variables: Variables to pass to the template

    Returns:
        Rendered template string

    Raises:
        jinja2.TemplateNotFound: If template doesn't exist
        jinja2.TemplateError: If template rendering fails

    """
    env = get_jinja_env()
    template = env.get_template(template_path)
    rendered = template.render(**variables)

    logger.debug(
        "template_rendered",
        template_path=template_path,
        variables_count=len(variables),
    )

    return rendered


def get_template_as_string(template_path: str) -> str:
    """Get raw template content without rendering.

    Useful for prompts that don't need variable substitution.

    Args:
        template_path: Path to template relative to templates/ dir

    Returns:
        Raw template content as string

    """
    env = get_jinja_env()
    template = env.get_template(template_path)
    return template.module.__loader__.get_source(env, template_path)[0]


def list_templates(subdir: str = "") -> list[str]:
    """List all templates in a subdirectory.

    Args:
        subdir: Subdirectory to list (e.g., "agents/tier1")

    Returns:
        List of template paths relative to templates/ dir

    """
    env = get_jinja_env()
    templates = env.loader.list_templates()

    if subdir:
        templates = [t for t in templates if t.startswith(subdir)]

    return sorted(templates)


class TemplatePaths:
    """Constants for template paths to avoid magic strings."""

    SUPERVISOR_ROUTING = "supervisor/routing.j2"

    AGENT_KEY_INSIGHTS = "agents/tier1/key_insights.j2"
    AGENT_PROS_CONS = "agents/tier1/pros_cons.j2"
    AGENT_AUDIENCE_FIT = "agents/tier1/audience_fit.j2"
    AGENT_ACTIONABLE = "agents/tier1/actionable.j2"

    AGENT_IMPLEMENTATION_PLANNER = "agents/tier2/implementation_planner.j2"
    AGENT_SECURITY_AUDITOR = "agents/tier2/security_auditor.j2"
    AGENT_PERFORMANCE_ANALYST = "agents/tier2/performance_analyst.j2"
    AGENT_TECH_COMPARATOR = "agents/tier2/tech_comparator.j2"
    AGENT_DEPENDENCY_MAPPER = "agents/tier2/dependency_mapper.j2"
    AGENT_TREND_VALIDATOR = "agents/tier2/trend_validator.j2"
    AGENT_INTEGRATION_FEASIBILITY = "agents/tier2/integration_feasibility.j2"
    AGENT_CODE_QUALITY_CRITIC = "agents/tier2/code_quality_critic.j2"
    AGENT_FACT_VALIDATOR = "agents/tier2/fact_validator.j2"

    AGENT_DEEP_RESEARCHER = "agents/tier3/deep_researcher.j2"
    AGENT_COMMUNITY_PULSE = "agents/tier3/community_pulse.j2"
    AGENT_KNOWLEDGE_CURATOR = "agents/tier3/knowledge_curator.j2"
    AGENT_LEARNING_PATH_ADVISOR = "agents/tier3/learning_path_advisor.j2"

    AGENT_RESEARCH_ANALYST = "agents/_archive/research_analyst.j2"
    AGENT_FRESHNESS_CHECKER = "agents/_archive/freshness_checker.j2"
    AGENT_ALTERNATIVES_FINDER = "agents/_archive/alternatives_finder.j2"
    AGENT_SOURCE_CREDIBILITY = "agents/_archive/source_credibility.j2"

    EVALUATOR_RELEVANCE = "evaluators/relevance.j2"
    EVALUATOR_DEPTH = "evaluators/depth.j2"
    EVALUATOR_ACCURACY = "evaluators/accuracy.j2"
    EVALUATOR_COHERENCE = "evaluators/coherence.j2"
    EVALUATOR_OVERALL = "evaluators/overall.j2"
