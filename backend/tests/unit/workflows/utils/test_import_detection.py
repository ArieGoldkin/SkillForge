"""Unit tests for import detection utilities."""

from app.shared.workflows.utils.import_detection import detect_code_patterns

@pytest.mark.unit


def test_detect_python_imports():
    """Test detection of Python import statements."""
    # Standard import
    content1 = "import fastapi\nfrom fastapi import FastAPI"
    result1 = detect_code_patterns(content1)
    assert result1["has_imports"] is True

    # From import
    content2 = "from typing import List, Dict"
    result2 = detect_code_patterns(content2)
    assert result2["has_imports"] is True

    # Nested import
    content3 = "from app.models import User, Post"
    result3 = detect_code_patterns(content3)
    assert result3["has_imports"] is True

    # No imports
    content4 = "This is just regular text without any code."
    result4 = detect_code_patterns(content4)
    assert result4["has_imports"] is False

    # Import in code block
    content5 = "Here's how to use it:\n```python\nimport requests\n```"
    result5 = detect_code_patterns(content5)
    assert result5["has_imports"] is True


def test_detect_package_files():
    """Test detection of package file mentions."""
    # requirements.txt
    content1 = "Add dependencies to requirements.txt"
    result1 = detect_code_patterns(content1)
    assert result1["has_package_files"] is True

    # pyproject.toml
    content2 = "Configure in pyproject.toml"
    result2 = detect_code_patterns(content2)
    assert result2["has_package_files"] is True

    # package.json
    content3 = "Update your package.json file"
    result3 = detect_code_patterns(content3)
    assert result3["has_package_files"] is True

    # Multiple package files
    content4 = "Use requirements.txt or pyproject.toml"
    result4 = detect_code_patterns(content4)
    assert result4["has_package_files"] is True

    # No package files
    content5 = "This is just regular text."
    result5 = detect_code_patterns(content5)
    assert result5["has_package_files"] is False


def test_detect_install_commands():
    """Test detection of installation commands."""
    # pip install
    content1 = "Run: pip install fastapi"
    result1 = detect_code_patterns(content1)
    assert result1["has_install_commands"] is True

    # npm install
    content2 = "npm install react"
    result2 = detect_code_patterns(content2)
    assert result2["has_install_commands"] is True

    # yarn add
    content3 = "yarn add express"
    result3 = detect_code_patterns(content3)
    assert result3["has_install_commands"] is True

    # poetry add
    content4 = "poetry add pydantic"
    result4 = detect_code_patterns(content4)
    assert result4["has_install_commands"] is True

    # No install commands
    content5 = "This is just regular text."
    result5 = detect_code_patterns(content5)
    assert result5["has_install_commands"] is False


def test_detect_frameworks():
    """Test detection of framework mentions."""
    # FastAPI
    content1 = "FastAPI is a modern web framework"
    result1 = detect_code_patterns(content1)
    assert result1["has_frameworks"] is True

    # React
    content2 = "Build with React and Next.js"
    result2 = detect_code_patterns(content2)
    assert result2["has_frameworks"] is True

    # Django
    content3 = "Django is a Python framework"
    result3 = detect_code_patterns(content3)
    assert result3["has_frameworks"] is True

    # Multiple frameworks
    content4 = "Compare FastAPI vs Django"
    result4 = detect_code_patterns(content4)
    assert result4["has_frameworks"] is True

    # No frameworks
    content5 = "This is just regular text."
    result5 = detect_code_patterns(content5)
    assert result5["has_frameworks"] is False


def test_detect_code_patterns_integration():
    """Test combined pattern detection."""
    # All patterns present
    content1 = """
    import fastapi
    from fastapi import FastAPI

    Add to requirements.txt:
    pip install fastapi uvicorn

    FastAPI is a modern framework.
    """
    result1 = detect_code_patterns(content1)
    assert result1["has_imports"] is True
    assert result1["has_package_files"] is True
    assert result1["has_install_commands"] is True
    assert result1["has_frameworks"] is True

    # Some patterns present
    content2 = """
    import requests
    pip install requests
    """
    result2 = detect_code_patterns(content2)
    assert result2["has_imports"] is True
    assert result2["has_install_commands"] is True
    assert result2["has_package_files"] is False
    assert result2["has_frameworks"] is False

    # No patterns
    content3 = "This is just regular text without any code patterns."
    result3 = detect_code_patterns(content3)
    assert result3["has_imports"] is False
    assert result3["has_package_files"] is False
    assert result3["has_install_commands"] is False
    assert result3["has_frameworks"] is False


def test_detect_code_patterns_performance_indicators():
    """Test detection of performance-critical keywords."""
    content = """
    from fastapi import FastAPI
    import asyncpg
    import redis

    # We need to benchmark the latency
    """
    patterns = detect_code_patterns(content)
    assert patterns["has_performance_indicators"] is True
    assert patterns["has_security_indicators"] is False  # Ensure no false positives


def test_detect_code_patterns_security_indicators():
    """Test detection of security-critical keywords."""
    content = """
    from passlib.context import CryptContext
    import python-jose

    # Check for SQL injection vulnerabilities
    """
    patterns = detect_code_patterns(content)
    assert patterns["has_security_indicators"] is True
    assert patterns["has_performance_indicators"] is False


def test_detect_code_patterns_comparison_logic():
    """Test detection of comparison scenarios."""
    # Scenario 1: Multiple frameworks
    content_multi = "We generate code for FastAPI and Django and React."
    patterns_multi = detect_code_patterns(content_multi)
    assert patterns_multi["has_comparison_indicators"] is True
    frameworks = patterns_multi["frameworks_detected"]
    assert isinstance(frameworks, list)
    assert set(frameworks) == {"fastapi", "django", "react"}

    # Scenario 2: Explicit comparison keyword
    content_explicit = "Let's compare vs the alternative approach."
    patterns_explicit = detect_code_patterns(content_explicit)
    assert patterns_explicit["has_comparison_indicators"] is True

    # Scenario 3: Single framework (no comparison)
    content_single = "Just using FastAPI here."
    patterns_single = detect_code_patterns(content_single)
    assert patterns_single["has_comparison_indicators"] is False
