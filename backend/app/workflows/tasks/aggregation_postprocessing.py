"""Post-processing and validation for aggregated insights."""

from typing import Any

# Constants for validation
MIN_EXEC_SUMMARY_SENTENCES = 2
MAX_EXEC_SUMMARY_SENTENCES = 3
MIN_KEY_FINDINGS = 3
MAX_KEY_FINDINGS = 7


def validate_and_format_aggregated_insights(
    aggregated_insights_dict: dict[str, Any],
) -> dict[str, Any]:
    """Validate and format aggregated insights output.

    Ensures executive_summary is 2-3 sentences and key_findings is 3-7 items.

    Args:
        aggregated_insights_dict: Raw aggregated insights dictionary from LLM

    Returns:
        Validated and formatted aggregated insights dictionary

    """
    # Ensure executive_summary is 2-3 sentences
    exec_summary = str(aggregated_insights_dict.get("executive_summary", ""))
    sentences = [s.strip() for s in exec_summary.split(".") if s.strip()]
    if len(sentences) < MIN_EXEC_SUMMARY_SENTENCES:
        # Pad with placeholder if too short
        aggregated_insights_dict["executive_summary"] = exec_summary
    elif len(sentences) > MAX_EXEC_SUMMARY_SENTENCES:
        # Truncate to 3 sentences
        aggregated_insights_dict["executive_summary"] = (
            ". ".join(sentences[:MAX_EXEC_SUMMARY_SENTENCES]) + "."
        )

    # Ensure key_findings is 3-7 items
    key_findings_raw = aggregated_insights_dict.get("key_findings", [])
    if not isinstance(key_findings_raw, list):
        key_findings: list[str] = []
    else:
        key_findings = [str(kf) for kf in key_findings_raw]

    if len(key_findings) < MIN_KEY_FINDINGS:
        # Pad with placeholder if too short
        while len(key_findings) < MIN_KEY_FINDINGS:
            key_findings.append("Additional analysis required")
    elif len(key_findings) > MAX_KEY_FINDINGS:
        # Truncate to 7 items
        key_findings = key_findings[:MAX_KEY_FINDINGS]
    aggregated_insights_dict["key_findings"] = key_findings

    return aggregated_insights_dict
