"""LangSmith query utilities for filtering and analyzing traces.

This module provides helper functions for querying LangSmith traces while
excluding GeneratorExit errors that occur during normal cleanup operations.

Note: This module is in the tools directory as it's only used for diagnostic
scripts, not in production code.
"""

from typing import Any

from langsmith import Client


def list_runs_without_generator_exit(
    project_name: str,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """List runs excluding GeneratorExit errors.

    Filters out traces that contain GeneratorExit errors, which typically
    occur during normal async generator cleanup and are not real errors.

    Args:
        project_name: Name of the LangSmith project
        **kwargs: Additional arguments passed to client.list_runs()

    Returns:
        List of run dictionaries that don't contain GeneratorExit errors

    Example:
        ```python
        from tools.langsmith.queries import list_runs_without_generator_exit

        runs = list_runs_without_generator_exit(
            project_name="news-analysis",
            limit=10,
        )
        ```

    """
    client = Client()
    return list(
        client.list_runs(
            project_name=project_name,
            filter='and(not(has(error, "GeneratorExit")), eq(status, "success"))',
            **kwargs,
        )
    )


def list_failed_runs_without_generator_exit(
    project_name: str,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """List failed runs excluding GeneratorExit errors.

    Filters failed traces to exclude GeneratorExit errors, focusing on
    actual failure cases that need investigation.

    Args:
        project_name: Name of the LangSmith project
        **kwargs: Additional arguments passed to client.list_runs()

    Returns:
        List of failed run dictionaries that don't contain GeneratorExit errors

    Example:
        ```python
        from tools.langsmith.queries import list_failed_runs_without_generator_exit

        failed_runs = list_failed_runs_without_generator_exit(
            project_name="news-analysis",
            limit=10,
        )
        ```

    """
    client = Client()
    return list(
        client.list_runs(
            project_name=project_name,
            filter='and(not(has(error, "GeneratorExit")), neq(status, "success"))',
            **kwargs,
        )
    )


def get_generator_exit_count(
    project_name: str,
    **kwargs: Any,
) -> int:
    """Get count of runs with GeneratorExit errors.

    Useful for monitoring the effectiveness of GeneratorExit handling
    improvements over time.

    Args:
        project_name: Name of the LangSmith project
        **kwargs: Additional arguments passed to client.list_runs()

    Returns:
        Count of runs containing GeneratorExit errors

    Example:
        ```python
        from tools.langsmith.queries import get_generator_exit_count

        count = get_generator_exit_count(
            project_name="news-analysis",
            limit=1000,  # Check last 1000 runs
        )
        print(f"GeneratorExit errors: {count}")
        ```

    """
    client = Client()
    runs = list(
        client.list_runs(
            project_name=project_name,
            filter='has(error, "GeneratorExit")',
            **kwargs,
        )
    )
    return len(runs)


def fetch_trace_with_all_runs(trace_id: str) -> dict[str, Any]:
    """Fetch a trace including all runs (including hidden/low-level runs).

    Retrieves a complete trace tree including all child runs, which helps
    identify GeneratorExit traces that may be hidden in the UI.

    Args:
        trace_id: The trace ID (run ID) to fetch

    Returns:
        Dictionary containing trace details and all runs

    Example:
        ```python
        from tools.langsmith.queries import fetch_trace_with_all_runs

        trace_data = fetch_trace_with_all_runs("trace-id-here")
        print(f"Total runs: {len(trace_data.get('runs', []))}")
        ```

    """
    client = Client()

    # Fetch the root run
    root_run = client.read_run(trace_id)

    # Fetch all runs in this trace (including hidden ones)
    all_runs = list(client.list_runs(trace_id=trace_id))

    return {
        "trace_id": trace_id,
        "root_run": root_run,
        "all_runs": all_runs,
        "total_runs": len(all_runs),
    }


def identify_generator_exit_runs(trace_id: str) -> dict[str, Any]:
    """Identify GeneratorExit runs in a trace.

    Analyzes all runs in a trace to find GeneratorExit errors and categorize
    them as cleanup traces (expected) vs execution errors (unexpected).

    Args:
        trace_id: The trace ID to analyze

    Returns:
        Dictionary with GeneratorExit analysis:
        - cleanup_runs: List of cleanup GeneratorExit runs (expected)
        - execution_runs: List of execution GeneratorExit runs (errors)
        - summary: Counts and statistics

    Example:
        ```python
        from tools.langsmith.queries import identify_generator_exit_runs

        analysis = identify_generator_exit_runs("trace-id-here")
        print(f"Cleanup runs: {len(analysis['cleanup_runs'])}")
        print(f"Execution errors: {len(analysis['execution_runs'])}")
        ```

    """
    client = Client()

    # Fetch all runs in trace
    all_runs = list(client.list_runs(trace_id=trace_id))

    cleanup_runs = []
    execution_runs = []

    for run in all_runs:
        # Check if run has GeneratorExit error
        error = (
            run.get("error")
            if isinstance(run, dict)
            else (run.error if hasattr(run, "error") else None)
        )

        if error and "GeneratorExit" in str(error):
            run_dict = (
                run
                if isinstance(run, dict)
                else {
                    "id": run.id if hasattr(run, "id") else None,
                    "name": run.name if hasattr(run, "name") else None,
                    "run_type": run.run_type if hasattr(run, "run_type") else None,
                    "error": str(error),
                    "start_time": run.start_time if hasattr(run, "start_time") else None,
                    "end_time": run.end_time if hasattr(run, "end_time") else None,
                }
            )

            # Categorize based on run name and context
            run_name = run_dict.get("name", "")

            # Cleanup runs typically occur after completion or in cleanup contexts
            is_cleanup = (
                "cleanup" in run_name.lower()
                or run_dict.get("end_time") is not None  # Completed run
                or run_dict.get("run_type") in ("chain", "llm")  # Internal cleanup
            )

            if is_cleanup:
                cleanup_runs.append(run_dict)
            else:
                execution_runs.append(run_dict)

    return {
        "trace_id": trace_id,
        "cleanup_runs": cleanup_runs,
        "execution_runs": execution_runs,
        "summary": {
            "total_runs": len(all_runs),
            "cleanup_count": len(cleanup_runs),
            "execution_count": len(execution_runs),
            "has_generator_exit": len(cleanup_runs) > 0 or len(execution_runs) > 0,
        },
    }
