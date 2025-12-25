"""Import and code pattern detection utilities.

This module provides functions to detect code patterns in content that indicate
dependency analysis is needed, such as import statements, package files, and
installation commands.
"""

import re

# Minimum frameworks needed to trigger tech comparator auto-activation
MIN_FRAMEWORKS_FOR_COMPARISON = 2


def detect_code_patterns(content: str) -> dict[str, bool | list[str]]:
    """Detect code patterns that indicate dependency analysis needed.

    Detects:
    - Python import statements (import X, from X import Y)
    - Package file mentions (requirements.txt, pyproject.toml, package.json)
    - Installation commands (pip install, npm install, etc.)
    - Framework mentions (FastAPI, React, Django, etc.)

    Args:
        content: Text content to analyze

    Returns:
        Dictionary with detection results:
        - has_imports: True if import statements found
        - has_package_files: True if package files mentioned
        - has_install_commands: True if installation commands found
        - has_frameworks: True if framework names detected

    """
    # Detect Python imports
    # Matches: import X, from X import Y, from X.Y import Z
    python_import_pattern = re.compile(
        r"\b(?:import\s+\w+|from\s+[\w.]+\s+import\s+[\w.,\s*]+)",
        re.MULTILINE,
    )
    has_imports = bool(python_import_pattern.search(content))

    # Detect package file mentions
    package_file_pattern = re.compile(
        r"\b(?:requirements\.txt|pyproject\.toml|package\.json|"
        r"Pipfile|poetry\.lock|yarn\.lock|pnpm-lock\.yaml|"
        r"go\.mod|Cargo\.toml|pom\.xml|build\.gradle)\b",
        re.IGNORECASE,
    )
    has_package_files = bool(package_file_pattern.search(content))

    # Detect installation commands
    install_command_pattern = re.compile(
        r"\b(?:pip\s+install|npm\s+install|yarn\s+add|pnpm\s+add|"
        r"poetry\s+add|conda\s+install|go\s+get|cargo\s+add|"
        r"mvn\s+install|gradle\s+build)\b",
        re.IGNORECASE,
    )
    has_install_commands = bool(install_command_pattern.search(content))

    # Detect framework mentions (common frameworks)
    framework_pattern = re.compile(
        r"\b(?:fastapi|django|flask|react|vue|angular|next\.js|svelte|"
        r"express|nestjs|spring|laravel|rails|symfony|"
        r"asp\.net|dotnet|tornado|bottle|pyramid)\b",
        re.IGNORECASE,
    )
    has_frameworks = bool(framework_pattern.search(content))

    # ISSUE #178: Performance Critical Keywords
    # Detects: asyncpg, redis, starlette, cython, multiprocessing, profiling tools
    performance_pattern = re.compile(
        r"\b(?:asyncpg|redis|memcached|starlette|uvicorn|gunicorn|cython|multiprocessing|aiohttp|profiler|benchmark|latency|throughput)",
        re.IGNORECASE,
    )
    has_performance_indicators = bool(performance_pattern.search(content))

    # ISSUE #174: Security Critical Keywords
    # Detects: auth libraries, crypto, cors, jwt, passwords, secrets
    security_pattern = re.compile(
        r"\b(?:python-jose|passlib|bcrypt|cryptography|authlib|django-allauth|helmet|"
        r"cors|jwt|oauth|secret|password|vulnerability|xss|csrf|sql injection)",
        re.IGNORECASE,
    )
    has_security_indicators = bool(security_pattern.search(content))

    # ISSUE #177: Comparison Logic
    # Detects multiple frameworks or explicit comparison keywords
    comparison_pattern = re.compile(
        r"\b(?:vs|versus|compare|comparison|alternative|migrat(?:e|ion)|benchmark)", re.IGNORECASE
    )
    has_comparison_keywords = bool(comparison_pattern.search(content))

    # Dynamic detection of multiple frameworks for comparison
    frameworks_found = set()
    for fw in ["fastapi", "django", "flask", "react", "vue", "angular", "next", "svelte"]:
        if re.search(r"\b" + fw + r"\b", content, re.IGNORECASE):
            frameworks_found.add(fw)

    # Heuristic: Tech Comparator needed if 2+ frameworks or explicit comparison requested
    has_comparison_indicators = (
        len(frameworks_found) >= MIN_FRAMEWORKS_FOR_COMPARISON
    ) or has_comparison_keywords

    return {
        "has_imports": has_imports,
        "has_package_files": has_package_files,
        "has_install_commands": has_install_commands,
        "has_frameworks": has_frameworks,
        "has_performance_indicators": has_performance_indicators,
        "has_security_indicators": has_security_indicators,
        "has_comparison_indicators": has_comparison_indicators,
        "frameworks_detected": list(frameworks_found),
    }
