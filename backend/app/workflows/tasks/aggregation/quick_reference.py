"""Extract QuickReference data from agent findings.

This module implements the extraction logic for the QuickReference section
as specified in docs/ARTIFACT_RESEARCH_SUMMARY.md.

The extraction strategy maps agent findings to QuickReference fields:
- primary_technology: from tech_comparator.primary_tech
- complexity: from implementation_planner.estimated_time
- prerequisites: from dependency_mapper or implementation_planner
- critical_commands: extracted from implementation_planner.steps
- files_to_modify: from implementation_planner.steps[].files
- gotchas: from security_auditor.security_risks and code_quality_critic.code_issues
"""

import re
from typing import Any

from app.core.logging import get_logger
from app.workflows.tasks.schemas.aggregated_insights import GotchaItem, QuickReference

logger = get_logger(__name__)

# Limit constants for QuickReference fields
MAX_PREREQUISITES = 4
MAX_CRITICAL_COMMANDS = 6
MAX_FILES_TO_MODIFY = 10
MAX_GOTCHAS = 5

# Complexity level thresholds (in hours)
COMPLEXITY_BEGINNER_MAX_HOURS = 2
COMPLEXITY_INTERMEDIATE_MAX_HOURS = 4
COMPLEXITY_ADVANCED_MAX_HOURS = 8

# Technology extraction constants
MIN_TECH_WORDS_FOR_NAME = 2


def extract_quick_reference(agent_findings: list[dict[str, Any]]) -> QuickReference | None:
    """Extract QuickReference from agent findings.

    Args:
        agent_findings: List of agent findings dictionaries with agent_type and result fields

    Returns:
        QuickReference object if sufficient data is available, None otherwise.

    Note:
        Extraction Strategy:
        1. primary_technology: tech_comparator.primary_tech + version from dependencies
        2. complexity: implementation_planner.estimated_time → format as "Level (Est. X)"
         3. prerequisites: dependency_mapper.peer_dependencies or
            implementation_planner.prerequisites
        4. critical_commands: extract install commands from implementation_planner.steps or
           dependency_mapper.installation_notes
        5. files_to_modify: collect from implementation_planner.steps[].files
        6. gotchas: security_auditor.security_risks + code_quality_critic.code_issues

    """
    try:
        # Organize findings by agent type for easy access
        # Note: agent findings structure is {"agent_type": str, "findings": dict, ...}
        findings_by_type: dict[str, dict[str, Any]] = {}
        for finding in agent_findings:
            agent_type = finding.get("agent_type", "")
            # Try "findings" first (actual structure), fall back to "result" for compatibility
            result = finding.get("findings") or finding.get("result", {})
            if agent_type and result:
                findings_by_type[agent_type] = result

        # Extract primary technology
        primary_technology = _extract_primary_technology(findings_by_type)
        if not primary_technology:
            logger.warning(
                "quick_reference_extraction_failed",
                reason="No primary technology found",
            )
            return None

        # Extract complexity and time estimate
        complexity = _extract_complexity(findings_by_type)

        # Extract prerequisites
        prerequisites = _extract_prerequisites(findings_by_type)

        # Extract critical commands
        critical_commands = _extract_critical_commands(findings_by_type)

        # Extract files to modify
        files_to_modify = _extract_files_to_modify(findings_by_type)

        # Extract gotchas
        gotchas = _extract_gotchas(findings_by_type)

        # Validate we have enough data to create QuickReference
        if not primary_technology or not complexity:
            logger.warning(
                "quick_reference_extraction_incomplete",
                has_primary_technology=bool(primary_technology),
                has_complexity=bool(complexity),
            )
            return None

        quick_ref = QuickReference(
            primary_technology=primary_technology,
            complexity=complexity,
            prerequisites=prerequisites,
            critical_commands=critical_commands,
            files_to_modify=files_to_modify,
            gotchas=gotchas,
        )

        logger.info(
            "quick_reference_extracted",
            primary_technology=primary_technology,
            prerequisites_count=len(prerequisites),
            commands_count=len(critical_commands),
            files_count=len(files_to_modify),
            gotchas_count=len(gotchas),
        )

        return quick_ref

    except Exception as e:
        logger.error(
            "quick_reference_extraction_error",
            error=str(e),
            exc_info=True,
        )
        return None


def _extract_primary_technology(findings_by_type: dict[str, dict[str, Any]]) -> str:  # noqa: PLR0912
    """Extract primary technology from tech_comparator.

    Format: "TechName version" (e.g., "LangGraph 0.6.7")

    Fallback order:
    1. tech_comparator.primary_tech
    2. dependency_mapper.required_dependencies[0]
    3. implementation_planner.steps (infer from first step action)
    4. trend_validator technology mentions
    """
    tech_comparator = findings_by_type.get("tech_comparator", {})
    primary_tech: str = str(tech_comparator.get("primary_tech", "") or "")

    if not primary_tech:
        # Fallback 1: try to infer from dependency mapper
        dep_mapper = findings_by_type.get("dependency_mapper", {})
        required_deps = dep_mapper.get("required_dependencies", [])
        if required_deps:
            first_dep = required_deps[0]
            if isinstance(first_dep, dict):
                name = first_dep.get("name", "")
                version = first_dep.get("version", "")
                if name:
                    primary_tech = f"{name} {version}".strip()

    if not primary_tech:
        # Fallback 2: Extract from implementation_planner prerequisites
        impl_planner = findings_by_type.get("implementation_planner", {})
        prerequisites = impl_planner.get("prerequisites", [])
        if prerequisites and isinstance(prerequisites, list):
            for prereq in prerequisites:
                if isinstance(prereq, str) and prereq.strip():
                    primary_tech = prereq.strip()
                    break

    if not primary_tech:
        # Fallback 3: Extract from trend_validator if it mentions specific technologies
        trend = findings_by_type.get("trend_validator", {})
        current_adoption = trend.get("current_adoption", "")
        if current_adoption and isinstance(current_adoption, str):
            # Try to extract a technology name from the adoption description
            # Look for patterns like "Spring Boot", "Test Pyramid", etc.
            words = current_adoption.split()
            if len(words) >= MIN_TECH_WORDS_FOR_NAME:
                # Take first two capitalized words as potential tech name
                tech_words = []
                for word in words[:5]:
                    clean_word = word.strip(".,;:()[]")
                    if clean_word and clean_word[0].isupper():
                        tech_words.append(clean_word)
                    if len(tech_words) >= MIN_TECH_WORDS_FOR_NAME:
                        break
                if tech_words:
                    primary_tech = " ".join(tech_words)

    # Try to add version info from dependency_mapper if not present
    if primary_tech and not any(char.isdigit() for char in primary_tech):
        dep_mapper = findings_by_type.get("dependency_mapper", {})
        required_deps = dep_mapper.get("required_dependencies", [])
        for dep in required_deps:
            if isinstance(dep, dict):
                name = dep.get("name", "")
                version = dep.get("version", "")
                if (
                    name.lower() in primary_tech.lower() or primary_tech.lower() in name.lower()
                ) and version:
                    primary_tech = f"{primary_tech} {version}".strip()
                    break

    return primary_tech


def _extract_complexity(findings_by_type: dict[str, dict[str, Any]]) -> str:
    """Extract complexity from implementation_planner.

    Format: "Level (Est. X-Y hours)" (e.g., "Intermediate (Est. 3-4 hours)")
    """
    impl_planner = findings_by_type.get("implementation_planner", {})
    estimated_time = impl_planner.get("estimated_time", "")

    if not estimated_time:
        return "Intermediate (Est. 3-4 hours)"  # Reasonable default

    # Map estimated time to complexity level
    estimated_lower = estimated_time.lower()

    if "hour" in estimated_lower:
        # Try to extract hours
        try:
            # Look for patterns like "2-3 hours", "1 hour", "3 hours"
            hours_match = re.search(r"(\d+)(?:-(\d+))?\s*(?:hour|hr)", estimated_lower)
            if hours_match:
                min_hours = int(hours_match.group(1))
                max_hours = int(hours_match.group(2)) if hours_match.group(2) else min_hours

                if max_hours <= COMPLEXITY_BEGINNER_MAX_HOURS:
                    level = "Beginner"
                elif max_hours <= COMPLEXITY_INTERMEDIATE_MAX_HOURS:
                    level = "Intermediate"
                elif max_hours <= COMPLEXITY_ADVANCED_MAX_HOURS:
                    level = "Advanced"
                else:
                    level = "Expert"

                return f"{level} (Est. {estimated_time})"
        except (ValueError, AttributeError):
            pass
    elif "day" in estimated_lower:
        # Multi-day projects are Advanced or Expert
        try:
            days_match = re.search(r"(\d+)(?:-(\d+))?\s*(?:day|days)", estimated_lower)
            if days_match:
                min_days = int(days_match.group(1))
                level = "Expert" if min_days > 1 else "Advanced"
                return f"{level} (Est. {estimated_time})"
        except (ValueError, AttributeError):
            pass

    # If we can't parse it, return as-is with Intermediate level
    return f"Intermediate (Est. {estimated_time})"


def _extract_prerequisites(findings_by_type: dict[str, dict[str, Any]]) -> list[str]:
    """Extract prerequisites from dependency_mapper or implementation_planner.

    Max 4 items with version numbers.
    """
    prerequisites: list[str] = []

    # First, check dependency_mapper.peer_dependencies
    dep_mapper = findings_by_type.get("dependency_mapper", {})
    peer_deps = dep_mapper.get("peer_dependencies", [])
    if isinstance(peer_deps, list):
        prerequisites.extend(peer_deps[:MAX_PREREQUISITES])

    # If we don't have enough, check implementation_planner.prerequisites
    if len(prerequisites) < MAX_PREREQUISITES:
        impl_planner = findings_by_type.get("implementation_planner", {})
        impl_prereqs = impl_planner.get("prerequisites", [])
        if isinstance(impl_prereqs, list):
            for prereq in impl_prereqs:
                if len(prerequisites) >= MAX_PREREQUISITES:
                    break
                if prereq not in prerequisites:
                    prerequisites.append(prereq)

    return prerequisites[:MAX_PREREQUISITES]


def _extract_critical_commands(findings_by_type: dict[str, dict[str, Any]]) -> list[str]:  # noqa: PLR0912
    """Extract critical installation commands.

    Max 6 commands from implementation_planner.steps or dependency_mapper.installation_notes.
    """
    commands: list[str] = []

    # First, check dependency_mapper.installation_notes for install commands
    dep_mapper = findings_by_type.get("dependency_mapper", {})
    install_notes = dep_mapper.get("installation_notes", [])
    if isinstance(install_notes, list):
        for note in install_notes:
            if isinstance(note, str):
                # Look for command-like strings (starting with npm, pip, yarn, etc.)
                note_lower = note.strip().lower()
                if any(
                    note_lower.startswith(cmd)
                    for cmd in ["pip install", "npm install", "yarn add", "poetry add", "go get"]
                ):
                    commands.append(note.strip())
                    if len(commands) >= MAX_CRITICAL_COMMANDS:
                        break

    # If we don't have enough, extract from implementation_planner.steps
    if len(commands) < MAX_CRITICAL_COMMANDS:
        impl_planner = findings_by_type.get("implementation_planner", {})
        steps = impl_planner.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if len(commands) >= MAX_CRITICAL_COMMANDS:
                    break
                if isinstance(step, dict):
                    action = step.get("action", "")
                    # Look for installation-related actions
                    action_lower = action.lower()
                    if any(
                        keyword in action_lower
                        for keyword in ["install", "setup", "configure", "initialize"]
                    ):
                        # Try to extract command-like strings from the action
                        # Simple heuristic: look for backtick-wrapped commands
                        cmd_matches = re.findall(r"`([^`]+)`", action)
                        for cmd in cmd_matches:
                            if cmd not in commands:
                                commands.append(cmd)
                                if len(commands) >= MAX_CRITICAL_COMMANDS:
                                    break

    return commands[:MAX_CRITICAL_COMMANDS]


def _extract_files_to_modify(findings_by_type: dict[str, dict[str, Any]]) -> list[str]:
    """Extract files to create/modify from implementation_planner.steps.

    Max 10 files with full paths.
    """
    files: list[str] = []
    seen_files: set[str] = set()

    impl_planner = findings_by_type.get("implementation_planner", {})
    steps = impl_planner.get("steps", [])

    if isinstance(steps, list):
        for step in steps:
            if len(files) >= MAX_FILES_TO_MODIFY:
                break
            if isinstance(step, dict):
                step_files = step.get("files", [])
                if isinstance(step_files, list):
                    for file_path in step_files:
                        if len(files) >= MAX_FILES_TO_MODIFY:
                            break
                        if isinstance(file_path, str) and file_path not in seen_files:
                            files.append(file_path)
                            seen_files.add(file_path)

    return files[:MAX_FILES_TO_MODIFY]


def _extract_gotchas(findings_by_type: dict[str, dict[str, Any]]) -> list[GotchaItem]:
    """Extract gotchas from security_auditor and code_quality_critic.

    Max 5 items with issue, symptom, and quick_fix.
    """
    gotchas: list[GotchaItem] = []

    # Extract from security_auditor.security_risks
    security_auditor = findings_by_type.get("security_auditor", {})
    security_risks = security_auditor.get("security_risks", [])
    if isinstance(security_risks, list):
        for risk in security_risks:
            if len(gotchas) >= MAX_GOTCHAS:
                break
            if isinstance(risk, dict):
                # Map security risk to gotcha
                risk_issue = risk.get("risk_type", "Security risk")
                description = risk.get("description", "")
                mitigation = risk.get("mitigation", "")
                severity = risk.get("severity", "")

                if description and mitigation:
                    gotcha = GotchaItem(
                        issue=f"{risk_issue.replace('_', ' ').title()}: {description}",
                        symptom=f"Security vulnerability ({severity} severity)",
                        quick_fix=mitigation,
                    )
                    gotchas.append(gotcha)

    # Extract from code_quality_critic.code_issues
    if len(gotchas) < MAX_GOTCHAS:
        code_critic = findings_by_type.get("code_quality_critic", {})
        code_issues = code_critic.get("code_issues", [])
        if isinstance(code_issues, list):
            for code_issue in code_issues:
                if len(gotchas) >= MAX_GOTCHAS:
                    break
                if isinstance(code_issue, dict):
                    # Map code issue to gotcha
                    issue_type = code_issue.get("issue_type", "Code quality issue")
                    description = code_issue.get("description", "")
                    suggestion = code_issue.get("suggestion", "")
                    severity = code_issue.get("severity", "")

                    if description and suggestion:
                        # Infer symptom from description
                        symptom = f"Code quality concern ({severity} severity)"
                        gotcha = GotchaItem(
                            issue=f"{issue_type.replace('_', ' ').title()}: {description}",
                            symptom=symptom,
                            quick_fix=suggestion,
                        )
                        gotchas.append(gotcha)

    return gotchas[:MAX_GOTCHAS]
