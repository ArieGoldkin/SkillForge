"""Template utilities for Jinja2 rendering.

Provides centralized template loading and rendering with caching.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Base directory for templates (relative to this file)
TEMPLATE_BASE_DIR = Path(__file__).parent.parent


@lru_cache(maxsize=10)
def _get_jinja_env(template_dir: str) -> Environment:
    """Get cached Jinja2 environment for template directory.

    Args:
        template_dir: Directory path containing templates

    Returns:
        Configured Jinja2 Environment

    """
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # Add custom filters
    env.filters["tojson"] = lambda obj, indent=2: json.dumps(obj, indent=indent)
    return env


def render_jinja_template(
    template_name: str,
    context: dict[str, Any],
    template_dir: str | None = None,
) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        template_name: Name of the template file (e.g., "aggregation_findings.j2")
        context: Dictionary of variables to pass to template
        template_dir: Optional custom template directory (defaults to workflows/tasks/templates)

    Returns:
        Rendered template string

    """
    if template_dir is None:
        # Default to workflows/tasks/templates
        template_dir = str(TEMPLATE_BASE_DIR / "workflows" / "tasks" / "templates")
    elif not Path(template_dir).is_absolute():
        # Resolve relative to base if relative path provided
        template_dir = str(TEMPLATE_BASE_DIR / template_dir)

    env = _get_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**context)
