"""Import and code pattern detection utilities.

This module provides functions to detect code patterns in content that indicate
dependency analysis is needed, such as import statements, package files, and
installation commands.
"""

import re


def detect_code_patterns(content: str) -> dict[str, bool]:
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
        r"\b(?:fastapi|django|flask|react|vue|angular|next\.js|"
        r"express|nestjs|spring|laravel|rails|symfony|"
        r"asp\.net|dotnet|tornado|bottle|pyramid)\b",
        re.IGNORECASE,
    )
    has_frameworks = bool(framework_pattern.search(content))

    return {
        "has_imports": has_imports,
        "has_package_files": has_package_files,
        "has_install_commands": has_install_commands,
        "has_frameworks": has_frameworks,
    }
