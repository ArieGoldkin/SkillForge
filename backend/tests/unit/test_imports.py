"""Regression tests for import behavior.

These tests ensure the application can be imported without requiring
environment variables like DATABASE_URL. This is critical for CI environments
that run linting, type checking, and unit tests without a database.
"""

import subprocess
import sys

import pytest


class TestImportWithoutDatabaseUrl:
    """Test that app modules can be imported without DATABASE_URL.

    These tests run in a subprocess with DATABASE_URL explicitly unset
    to simulate the CI environment.
    """

    @pytest.mark.parametrize(
        "module",
        [
            "app.main",
            "app.api.v1.analyze",
            "app.api.v1.workflow_runner",
            "app.workflows.analysis",
            "app.workflows.tasks",
        ],
    )
    def test_module_imports_without_database_url(self, module: str):
        """Test that module can be imported without DATABASE_URL set.

        This is a regression test for the CI import failure where the import
        chain triggered DATABASE_URL validation at module load time.

        The test runs in a subprocess to ensure a clean environment without
        DATABASE_URL, simulating the CI environment.
        """
        # Run import in subprocess with DATABASE_URL explicitly unset
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import {module}; print('OK')",
            ],
            capture_output=True,
            text=True,
            env={
                # Minimal environment - explicitly exclude DATABASE_URL
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                # Python needs these
                "PYTHONPATH": ".",
            },
            cwd="/Users/yonatangross/coding/SkillForge/backend",
            timeout=30,
        )

        # Check for success
        assert result.returncode == 0, (
            f"Failed to import {module} without DATABASE_URL.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
            f"This likely means a module-level import of app.db.session was added.\n"
            f"Fix: Move the import inside the function that uses it."
        )
        assert "OK" in result.stdout

    def test_conftest_imports_without_database_url(self):
        """Test that conftest.py can be loaded without DATABASE_URL.

        This specifically tests the pytest configuration file which is
        loaded before any tests run.
        """
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from tests.conftest import *; print('OK')",
            ],
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "PYTHONPATH": ".",
            },
            cwd="/Users/yonatangross/coding/SkillForge/backend",
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Failed to import conftest.py without DATABASE_URL.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        assert "OK" in result.stdout
