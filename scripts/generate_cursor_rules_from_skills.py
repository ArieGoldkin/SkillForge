#!/usr/bin/env python3
"""Generate Cursor Project Rules from SkillForge `.claude/skills/*`.

This script enforces a 1:1 mapping:
  `.claude/skills/<skill>/` -> `.cursor/rules/<skill>/RULE.md`

It generates **thin rules** (short checklists + pointers back to the skill files)
to minimize context pollution, per Cursor Rules best practices (2025-12-15).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
RULES_DIR = REPO_ROOT / ".cursor" / "rules"

MAX_RULE_LINES = 500

REQUIRED_SECTION_HEADINGS = [
    "## Purpose",
    "## When to apply",
    "## When NOT to apply",
    "## Do / Don’t (thin checklist)",
    "## Output contract",
    "## Deep references (open only when needed)",
]


@dataclass(frozen=True)
class SkillInfo:
    name: str
    description: str
    triggers: list[str]
    globs: list[str]
    has_references: bool
    has_templates: bool
    has_checklists: bool
    has_examples: bool


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_globs(skill_name: str) -> list[str]:
    # Keep this conservative: globs only when they clearly prevent misfires.
    # Prefer Apply Intelligently for most rules; only scope by files when it's truly domain-specific.
    if skill_name in {"react-server-components-framework", "design-system-starter"}:
        return ["frontend/**/*.{ts,tsx}"]
    return []


def _extract_triggers(capabilities: dict) -> list[str]:
    triggers = capabilities.get("triggers", {})
    hi = triggers.get("high_confidence", [])
    mid = triggers.get("medium_confidence", [])
    # Keep short for prompt hygiene
    return [*hi[:4], *mid[:2]]


def _skill_info(skill_dir: Path) -> SkillInfo:
    capabilities_path = skill_dir / "capabilities.json"
    data = _read_json(capabilities_path)
    name = str(data.get("name", skill_dir.name))
    description = str(data.get("description", "")).strip()
    triggers = _extract_triggers(data)
    return SkillInfo(
        name=name,
        description=description,
        triggers=triggers,
        globs=_detect_globs(name),
        has_references=(skill_dir / "references").exists(),
        has_templates=(skill_dir / "templates").exists(),
        has_checklists=(skill_dir / "checklists").exists(),
        has_examples=(skill_dir / "examples").exists(),
    )


def _list_rel_files(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    return sorted(str(p.relative_to(REPO_ROOT)) for p in dir_path.rglob("*") if p.is_file())

def _yaml_quote(value: str) -> str:
    # YAML double-quoted string with conservative escaping.
    return '"' + value.replace("\\", "\\\\").replace('"', "'").strip() + '"'


def _render_rule_md(skill: SkillInfo) -> str:
    fm_lines = ["---", f"description: {_yaml_quote(skill.description or skill.name)}", "alwaysApply: false"]
    if skill.globs:
        fm_lines.append("globs:")
        fm_lines.extend([f"  - {g}" for g in skill.globs])
    fm_lines.append("---")

    trigger_line = ", ".join(skill.triggers) if skill.triggers else "N/A"

    lines: list[str] = []
    lines.extend(fm_lines)
    lines.append("")
    lines.append(f"# {skill.name}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(skill.description or "Use this rule to apply the corresponding SkillForge skill guidance.")
    lines.append("")
    lines.append("## When to apply")
    lines.append("")
    lines.append("- Apply when the task matches the capability keywords/triggers for this skill.")
    lines.append(f"- If unsure, open `@.claude/skills/{skill.name}/capabilities.json` and check `capabilities.*.solves`.")
    lines.append("")
    lines.append(f"Trigger hints from `capabilities.json` (keep this lightweight): `{trigger_line}`")
    lines.append("")
    lines.append("## When NOT to apply")
    lines.append("")
    lines.append("- If the task is unrelated to this skill’s domain and would add noise.")
    lines.append("- If the baseline rule already fully covers the need (workflow/safety/evidence) and no specialized guidance is required.")
    lines.append("")
    lines.append("## Do / Don’t (thin checklist)")
    lines.append("")
    lines.extend(
        [
            "- Do keep guidance **actionable** (short steps + clear outputs).",
            "- Do open the skill’s `capabilities.json` first to confirm relevance before loading large references.",
            "- Do use the skill’s `references/`, `templates/`, `checklists/`, and `examples/` as the source of truth.",
            "- Do prefer pointing to files over copying large blocks into chat.",
            "- Do tailor advice to the repo’s actual stack and constraints (don’t assume different frameworks).",
            "- Do keep changes small and verifiable; add tests when behavior changes.",
            "- Do preserve existing architecture patterns; don’t introduce new layers without justification.",
            "- Don’t introduce new repo-wide policies here (those belong in `skillforge-baseline`).",
            "- Don’t recommend unsafe commands or destructive operations without explicit user request.",
            "- Don’t add dependencies casually; justify and document any new dependency.",
            "- Don’t output long, ungrounded “best practices” essays—use checklists and references.",
            "- Don’t proceed if the task needs a different skill—switch to the correct rule instead.",
        ]
    )
    lines.append("")
    lines.append("## Output contract")
    lines.append("")
    lines.extend(
        [
            "- Provide a short implementation outline referencing the relevant skill files used.",
            "- Call out the specific files you changed/created.",
            "- If you ran commands, include the command + exit code (or captured evidence).",
            "- If you didn’t run commands, say what should be run to verify.",
        ]
    )
    lines.append("")
    lines.append("## Deep references (open only when needed)")
    lines.append("")
    lines.append(f"- `@.claude/skills/{skill.name}/capabilities.json` (discovery + triggers)")
    lines.append(f"- `@.claude/skills/{skill.name}/SKILL.md` (overview + patterns)")
    if skill.has_references:
        lines.append(f"- Browse: `@.claude/skills/{skill.name}/references/`")
    if skill.has_templates:
        lines.append(f"- Templates: `@.claude/skills/{skill.name}/templates/`")
    if skill.has_checklists:
        lines.append(f"- Checklists: `@.claude/skills/{skill.name}/checklists/`")
    if skill.has_examples:
        lines.append(f"- Examples: `@.claude/skills/{skill.name}/examples/`")
    lines.append("")
    return "\n".join(lines)


def _write_rule(skill_dir: Path, skill: SkillInfo) -> Path:
    out_dir = RULES_DIR / skill.name
    out_path = out_dir / "RULE.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render_rule_md(skill), encoding="utf-8")
    return out_path


def _write_rules_index(skills: list[SkillInfo]) -> Path:
    lines: list[str] = []
    lines.append("# Cursor Rules (generated from .claude/skills)\n")
    lines.append("This directory mirrors `.claude/skills/*` into `.cursor/rules/*` as thin rules.\n")
    lines.append("## How to use\n")
    lines.append("- Baseline guardrails are always applied: `skillforge-baseline`.\n")
    lines.append("- Most rules are designed to **Apply Intelligently** (Cursor decides via the rule `description`).\n")
    lines.append("- Use `globs` only as a guardrail against irrelevant activation.\n")
    lines.append("## Rules index\n")
    for s in sorted(skills, key=lambda x: x.name):
        mode = "Apply Intelligently" if not s.globs else "Apply to Specific Files (globs present) / Apply Intelligently"
        globs = ", ".join(s.globs) if s.globs else "none"
        lines.append(f"- `{s.name}`: {mode}; globs: {globs}")
    lines.append("")
    lines.append("## Suggested validation prompts\n")
    lines.append("- \"Design a paginated FastAPI endpoint and error model\" (expect: `api-design-framework` + baseline)\n")
    lines.append("- \"Implement SSE progress streaming and reconnection\" (expect: `streaming-api-patterns` + baseline)\n")
    lines.append("- \"Add unit + integration tests for this new service\" (expect: `testing-strategy-builder` + baseline)\n")
    lines.append("- \"Do a quick security pass for auth + input validation\" (expect: `security-checklist` + baseline)\n")
    lines.append("- \"Create an ADR documenting a major architecture choice\" (expect: `architecture-decision-record` + baseline)\n")
    lines.append("- \"Optimize a slow query / endpoint\" (expect: `performance-optimization` + baseline)\n")
    lines.append("- \"Add structured logging + tracing hooks\" (expect: `observability-monitoring` + baseline)\n")
    lines.append("- \"Design a migration + indexes\" (expect: `database-schema-designer` + baseline)\n")
    lines.append("- \"Plan CI/CD deployment config\" (expect: `devops-deployment` + baseline)\n")
    lines.append("- \"Brainstorm approaches and create a decision matrix\" (expect: `brainstorming` + baseline)\n")
    out = RULES_DIR / "README.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _check_rules(skills: list[SkillInfo]) -> list[str]:
    problems: list[str] = []
    # Baseline rule must exist and always apply.
    baseline = RULES_DIR / "skillforge-baseline" / "RULE.md"
    if not baseline.exists():
        problems.append(f"missing baseline: {baseline.relative_to(REPO_ROOT)}")
    else:
        baseline_text = baseline.read_text(encoding="utf-8")
        if "alwaysApply: true" not in baseline_text.splitlines()[:20]:
            problems.append(f"baseline missing alwaysApply: true: {baseline.relative_to(REPO_ROOT)}")

    for s in skills:
        rule_path = RULES_DIR / s.name / "RULE.md"
        if not rule_path.exists():
            problems.append(f"missing rule: {rule_path.relative_to(REPO_ROOT)}")
            continue
        line_count = len(rule_path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_RULE_LINES:
            problems.append(f"rule too long ({line_count} lines): {rule_path.relative_to(REPO_ROOT)}")
        text = rule_path.read_text(encoding="utf-8")
        # Frontmatter sanity: must start with --- and include description + alwaysApply
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            problems.append(f"rule missing frontmatter start ---: {rule_path.relative_to(REPO_ROOT)}")
        else:
            try:
                end_idx = lines.index("---", 1)
            except ValueError:
                problems.append(f"rule missing frontmatter end ---: {rule_path.relative_to(REPO_ROOT)}")
            else:
                fm = "\n".join(lines[1:end_idx])
                if "description:" not in fm:
                    problems.append(f"rule missing description in frontmatter: {rule_path.relative_to(REPO_ROOT)}")
                if "alwaysApply:" not in fm:
                    problems.append(f"rule missing alwaysApply in frontmatter: {rule_path.relative_to(REPO_ROOT)}")
        # Required headings sanity: ensure structure exists (thin rule contract)
        for heading in REQUIRED_SECTION_HEADINGS:
            if heading not in text:
                problems.append(f"rule missing heading {heading!r}: {rule_path.relative_to(REPO_ROOT)}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write/update rules to .cursor/rules/")
    parser.add_argument("--check", action="store_true", help="Verify 1:1 mapping and size limits")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Stricter validation (frontmatter + required headings + baseline rule)",
    )
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        raise SystemExit(f"Skills directory not found: {SKILLS_DIR}")

    skill_dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "capabilities.json").exists()]
    skills = [_skill_info(p) for p in skill_dirs]

    if args.write:
        for d in skill_dirs:
            _write_rule(d, _skill_info(d))
        _write_rules_index(skills)

    if args.check or args.write or args.validate:
        problems = _check_rules(skills)
        if problems:
            print("FAILED:")
            for p in problems:
                print(f"- {p}")
            return 1
        print("OK")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


