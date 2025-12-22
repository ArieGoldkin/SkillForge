"""Helper functions for checking workflow abort signals.

Issue #441: Provides standardized abort signal checking to ensure all workflow
nodes properly respect the should_abort flag set by extraction failures.
"""

from app.core.logging import get_logger
from app.domains.analysis.workflows.state import AnalysisState

logger = get_logger(__name__)


def check_should_abort(state: AnalysisState) -> dict | None:
    """Check if workflow should abort and return early if needed.

    Returns None if should abort (node should return early).
    Returns {} if should continue (node should proceed).

    This helper ensures consistent abort signal checking across all workflow nodes.
    When extraction fails, should_abort is set to True, and all subsequent nodes
    should skip execution to avoid wasting resources.

    Args:
        state: Current workflow state

    Returns:
        None if should abort (node should return early with empty dict)
        {} if should continue (node should proceed with execution)

    Example:
        ```python
        async def my_node(state: AnalysisState) -> dict:
            abort_result = check_should_abort(state)
            if abort_result is None:
                return {}  # Skip execution

            # Continue with normal execution
            # ...
        ```

    """
    if state.get("should_abort"):
        analysis_id = state.get("analysis_id")
        abort_reason = state.get("abort_reason", "Unknown error")
        logger.debug(
            "workflow_node_skipped_abort",
            analysis_id=analysis_id,
            abort_reason=abort_reason,
        )
        return None
    return {}
