#!/usr/bin/env python3
"""CLI runner for retrieval smoke tests.

Provides a standalone entry point for running smoke tests with
configurable options for mode, verbosity, and reporting.

Usage:
    # Run all retrieval smoke tests
    python -m tests.smoke.retrieval.run_smoke_tests

    # Run specific search mode tests
    python -m tests.smoke.retrieval.run_smoke_tests --mode semantic
    python -m tests.smoke.retrieval.run_smoke_tests --mode hybrid
    python -m tests.smoke.retrieval.run_smoke_tests --mode keyword

    # Run with verbose output
    python -m tests.smoke.retrieval.run_smoke_tests -v

    # Generate JUnit XML report
    python -m tests.smoke.retrieval.run_smoke_tests --junit-xml results.xml

    # List available tests without running
    python -m tests.smoke.retrieval.run_smoke_tests --collect-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def get_test_directory() -> Path:
    """Get the path to the smoke test directory."""
    return Path(__file__).parent


def build_pytest_args(
    mode: str | None = None,
    verbose: bool = False,
    junit_xml: str | None = None,
    collect_only: bool = False,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build pytest command arguments.

    Args:
        mode: Specific search mode to test (semantic, keyword, hybrid)
        verbose: Enable verbose output
        junit_xml: Path for JUnit XML report
        collect_only: Only collect tests, don't run
        extra_args: Additional pytest arguments

    Returns:
        List of pytest command arguments

    """
    test_dir = get_test_directory()
    args = ["pytest", str(test_dir)]

    # Add markers for specific mode
    if mode:
        if mode == "semantic":
            args.extend(["-m", "semantic"])
        elif mode == "keyword":
            args.extend(["-m", "keyword"])
        elif mode == "hybrid":
            args.extend(["-m", "hybrid"])
        elif mode == "all":
            args.extend(["-m", "retrieval"])
        else:
            print(f"Warning: Unknown mode '{mode}', running all tests")

    # Always include smoke marker
    if "-m" not in args:
        args.extend(["-m", "smoke and retrieval"])

    # Verbosity
    if verbose:
        args.append("-v")

    # JUnit XML output
    if junit_xml:
        args.extend(["--junit-xml", junit_xml])

    # Collect only
    if collect_only:
        args.append("--collect-only")

    # Show captured output on failure
    args.append("-s")

    # Extra args
    if extra_args:
        args.extend(extra_args)

    return args


def run_smoke_tests(
    mode: str | None = None,
    verbose: bool = False,
    junit_xml: str | None = None,
    collect_only: bool = False,
    extra_args: list[str] | None = None,
) -> int:
    """Run retrieval smoke tests.

    Args:
        mode: Specific search mode to test
        verbose: Enable verbose output
        junit_xml: Path for JUnit XML report
        collect_only: Only collect tests, don't run
        extra_args: Additional pytest arguments

    Returns:
        Exit code from pytest

    """
    args = build_pytest_args(
        mode=mode,
        verbose=verbose,
        junit_xml=junit_xml,
        collect_only=collect_only,
        extra_args=extra_args,
    )

    print(f"Running: {' '.join(args)}")
    print("-" * 60)

    result = subprocess.run(args, check=False, cwd=get_test_directory().parent.parent.parent)

    return result.returncode


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run retrieval smoke tests for SkillForge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Run all retrieval smoke tests
  %(prog)s --mode semantic      Run only semantic search tests
  %(prog)s --mode hybrid        Run only hybrid search tests
  %(prog)s --mode keyword       Run only keyword search tests
  %(prog)s -v                   Run with verbose output
  %(prog)s --junit-xml out.xml  Generate JUnit XML report
  %(prog)s --collect-only       List tests without running

Markers:
  @pytest.mark.smoke      - All smoke tests
  @pytest.mark.retrieval  - Retrieval system tests
  @pytest.mark.semantic   - Semantic search tests
  @pytest.mark.keyword    - Keyword search tests
  @pytest.mark.hybrid     - Hybrid search tests
        """,
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["semantic", "keyword", "hybrid", "all"],
        help="Run tests for specific search mode",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--junit-xml",
        metavar="PATH",
        help="Generate JUnit XML report at PATH",
    )

    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect tests, don't run them",
    )

    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to pytest",
    )

    args = parser.parse_args()

    exit_code = run_smoke_tests(
        mode=args.mode,
        verbose=args.verbose,
        junit_xml=args.junit_xml,
        collect_only=args.collect_only,
        extra_args=args.extra_args if args.extra_args else None,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
