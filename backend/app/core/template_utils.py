"""Template utilities for Jinja2 rendering.

Provides centralized template loading and rendering with caching.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug for anchor links.

    Args:
        text: Text to slugify

    Returns:
        Lowercase hyphenated slug

    """
    if not text:
        return ""
    # Lowercase, replace spaces with hyphens, remove special chars
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"[\s_]+", "-", slug)  # Replace spaces/underscores with hyphens
    slug = re.sub(r"-+", "-", slug)  # Collapse multiple hyphens
    return slug.strip("-")


def fix_bullets(text: str) -> str:
    """Convert Unicode bullet characters to markdown list syntax.

    LLMs often output • or · instead of proper markdown - syntax.
    This filter fixes that for proper list rendering.

    Args:
        text: Text that may contain Unicode bullets

    Returns:
        Text with proper markdown list syntax

    """
    if not text:
        return ""

    # Split into lines and process each
    lines = text.split("\n")
    result_lines = []

    for line in lines:
        # Match lines starting with bullet characters (with optional whitespace)
        # Unicode bullets: • (U+2022), · (U+00B7), ● (U+25CF), ◦ (U+25E6), ▪ (U+25AA)
        bullet_match = re.match(r"^(\s*)[•·●◦▪]\s*(.+)$", line)
        if bullet_match:
            indent = bullet_match.group(1)
            content = bullet_match.group(2)
            result_lines.append(f"{indent}- {content}")
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def normalize_paragraphs(text: str) -> str:
    r"""Ensure proper paragraph breaks in markdown content.

    LLMs sometimes output multi-paragraph content without proper \n\n breaks.
    This filter adds breaks after bold section headers (e.g., **Title:**).

    Args:
        text: Markdown text that may lack proper paragraph breaks

    Returns:
        Text with normalized paragraph breaks

    """
    if not text:
        return ""

    # If text already has proper paragraph breaks, preserve it
    if "\n\n" in text:
        return text

    # Add paragraph break after bold headers with colons
    # Pattern: **Title:** followed by whitespace (but not already double newline)
    # Markdown bold with colon: **text:**
    return re.sub(r"(\*\*[^*]+:\*\*)\s+", r"\1\n\n", text)


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
    env.filters["slugify"] = slugify
    env.filters["fix_bullets"] = fix_bullets
    env.filters["normalize_paragraphs"] = normalize_paragraphs
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
        # Default to domains/analysis/workflows/tasks/templates
        template_dir = str(
            TEMPLATE_BASE_DIR / "domains" / "analysis" / "workflows" / "tasks" / "templates"
        )
    elif not Path(template_dir).is_absolute():
        # Resolve relative to base if relative path provided
        template_dir = str(TEMPLATE_BASE_DIR / template_dir)

    env = _get_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**context)
