#!/usr/bin/env python3
"""Diagnostic script to inspect LangSmith traces and identify GeneratorExit runs.

This script helps investigate traces to understand:
1. What runs are hidden in the UI
2. If hidden runs are GeneratorExit cleanup traces
3. Trace structure and execution flow

Usage:
    python scripts/inspect_langsmith_trace.py <trace_id>
    python scripts/inspect_langsmith_trace.py --trace-id <trace_id>
    python scripts/inspect_langsmith_trace.py --project <project_name> --limit 5
"""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.langsmith.queries import fetch_trace_with_all_runs, identify_generator_exit_runs


def format_run_summary(run: dict) -> str:
    """Format a run summary for display."""
    name = run.get("name", "unnamed")
    run_type = run.get("run_type", "unknown")
    error = run.get("error")
    has_error = error is not None and str(error) != "None"

    summary = f"  - {name} ({run_type})"
    if has_error:
        error_str = str(error)[:100]  # Truncate long errors
        summary += f" [ERROR: {error_str}]"

    return summary


def print_trace_analysis(trace_id: str) -> None:
    """Analyze and print trace details."""
    print("=" * 80)
    print(f"LangSmith Trace Analysis: {trace_id}")
    print("=" * 80)
    print()

    # Fetch trace with all runs
    print("Fetching trace data...")
    try:
        trace_data = fetch_trace_with_all_runs(trace_id)
    except (ValueError, KeyError, RuntimeError) as e:
        print(f"Error fetching trace: {e}")
        return

    root_run = trace_data.get("root_run")
    all_runs = trace_data.get("all_runs", [])

    print(f"Total runs in trace: {len(all_runs)}")
    print()

    # Root run info
    if root_run:
        root_dict = (
            root_run
            if isinstance(root_run, dict)
            else {
                "id": root_run.id if hasattr(root_run, "id") else None,
                "name": root_run.name if hasattr(root_run, "name") else None,
                "status": root_run.status if hasattr(root_run, "status") else None,
                "error": root_run.error if hasattr(root_run, "error") else None,
            }
        )
        print("Root Run:")
        print(f"  Name: {root_dict.get('name', 'unknown')}")
        print(f"  Status: {root_dict.get('status', 'unknown')}")
        if root_dict.get("error"):
            print(f"  Error: {root_dict['error']}")
        print()

    # Identify GeneratorExit runs
    print("Analyzing GeneratorExit runs...")
    try:
        gen_exit_analysis = identify_generator_exit_runs(trace_id)
    except (ValueError, KeyError, RuntimeError) as e:
        print(f"Error analyzing GeneratorExit: {e}")
        gen_exit_analysis = None

    if gen_exit_analysis:
        summary = gen_exit_analysis.get("summary", {})
        cleanup_runs = gen_exit_analysis.get("cleanup_runs", [])
        execution_runs = gen_exit_analysis.get("execution_runs", [])

        print("GeneratorExit Summary:")
        print(f"  Total runs: {summary.get('total_runs', 0)}")
        print(f"  Cleanup runs (expected): {summary.get('cleanup_count', 0)}")
        print(f"  Execution runs (errors): {summary.get('execution_count', 0)}")
        print()

        if cleanup_runs:
            print("Cleanup GeneratorExit Runs (Expected):")
            for run in cleanup_runs:
                print(format_run_summary(run))
            print()

        if execution_runs:
            print("Execution GeneratorExit Runs (Errors):")
            for run in execution_runs:
                print(format_run_summary(run))
            print()

    # List all runs
    print("All Runs in Trace:")
    for i, run in enumerate(all_runs, 1):
        run_dict = (
            run
            if isinstance(run, dict)
            else {
                "id": run.id if hasattr(run, "id") else None,
                "name": run.name if hasattr(run, "name") else None,
                "run_type": run.run_type if hasattr(run, "run_type") else None,
                "error": run.error if hasattr(run, "error") else None,
            }
        )
        print(f"{i}. {format_run_summary(run_dict)}")

    print()
    print("=" * 80)
    print("Analysis Complete")
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_langsmith_trace.py <trace_id>")
        print("   or: python scripts/inspect_langsmith_trace.py --trace-id <trace_id>")
        sys.exit(1)

    trace_id = None

    # Parse arguments
    if "--trace-id" in sys.argv:
        idx = sys.argv.index("--trace-id")
        if idx + 1 < len(sys.argv):
            trace_id = sys.argv[idx + 1]
    elif len(sys.argv) == 2:
        trace_id = sys.argv[1]
    else:
        print("Error: Please provide a trace ID")
        sys.exit(1)

    if not trace_id:
        print("Error: Trace ID not provided")
        sys.exit(1)

    print_trace_analysis(trace_id)


if __name__ == "__main__":
    main()
