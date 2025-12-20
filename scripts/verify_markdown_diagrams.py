#!/usr/bin/env python3
"""Verify Mermaid + ASCII art rendering in Markdown for GitHub.

This script performs two checks:
1) Mermaid validation: extracts ```mermaid blocks and renders each with Mermaid CLI.
2) ASCII art hygiene: ensures ASCII box-drawing diagrams are inside fenced code blocks
   and warns on very long code-block lines that will wrap badly in GitHub.

Mermaid rendering uses `npx @mermaid-js/mermaid-cli` (mmdc). This matches GitHub's
Mermaid dialect closely enough to catch syntax errors early.

Usage:
  python scripts/verify_markdown_diagrams.py
  python scripts/verify_markdown_diagrams.py --paths docs CLAUDE.md backend/data/README.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


MERMAID_FENCE_RE = re.compile(r"^```mermaid\s*$")
FENCE_RE = re.compile(r"^```(?P<lang>[A-Za-z0-9_-]+)?\s*$")
BOX_DRAWING_RE = re.compile(r"[┌┐└┘│─]")


@dataclass(frozen=True)
class MermaidBlock:
    file: Path
    start_line: int
    content: str


@dataclass(frozen=True)
class Problem:
    file: Path
    line: int
    code: str
    message: str
    severity: str  # "error" | "warn"


def _iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.is_file() and p.suffix.lower() == ".md":
            files.append(p)
    # Dedup while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def extract_mermaid_blocks(md_path: Path) -> list[MermaidBlock]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    blocks: list[MermaidBlock] = []
    in_mermaid = False
    start_line = 0
    buf: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if not in_mermaid and MERMAID_FENCE_RE.match(line):
            in_mermaid = True
            start_line = idx
            buf = []
            continue

        if in_mermaid and line.strip() == "```":
            blocks.append(MermaidBlock(file=md_path, start_line=start_line, content="\n".join(buf).strip() + "\n"))
            in_mermaid = False
            continue

        if in_mermaid:
            buf.append(line)

    # Unclosed mermaid fence is treated as a broken block (we still return it for context)
    if in_mermaid:
        blocks.append(MermaidBlock(file=md_path, start_line=start_line, content="\n".join(buf).strip() + "\n"))
    return blocks


def check_ascii_hygiene(md_path: Path, *, max_code_line_len: int) -> list[Problem]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    problems: list[Problem] = []

    in_fence = False

    for idx, line in enumerate(lines, start=1):
        m = FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
            else:
                in_fence = False
            continue

        # Box drawing characters outside code blocks usually render poorly in GitHub.
        if not in_fence and BOX_DRAWING_RE.search(line):
            problems.append(
                Problem(
                    file=md_path,
                    line=idx,
                    code="ASCII001",
                    message="Box-drawing characters found outside a fenced code block. Wrap ASCII art in ```text.",
                    severity="error",
                )
            )

        # Long lines inside code blocks (including mermaid/text) will wrap badly in GitHub.
        if in_fence and len(line) > max_code_line_len:
            problems.append(
                Problem(
                    file=md_path,
                    line=idx,
                    code="ASCII002",
                    message=f"Very long code-block line ({len(line)} chars). Consider wrapping or shortening (threshold {max_code_line_len}).",
                    severity="warn",
                )
            )

    return problems


def render_mermaid_blocks(blocks: list[MermaidBlock]) -> list[Problem]:
    problems: list[Problem] = []
    if not blocks:
        return problems

    with tempfile.TemporaryDirectory(prefix="skillforge-mermaid-") as tmpdir:
        tmp = Path(tmpdir)

        for i, b in enumerate(blocks, start=1):
            in_path = tmp / f"diagram-{i}.mmd"
            out_path = tmp / f"diagram-{i}.svg"
            in_path.write_text(b.content, encoding="utf-8")

            # Use npx to avoid requiring a global install.
            cmd = [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli",
                "-i",
                str(in_path),
                "-o",
                str(out_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except FileNotFoundError:
                problems.append(
                    Problem(
                        file=b.file,
                        line=b.start_line,
                        code="MERMAID000",
                        message="`npx` not found. Install Node.js/npm to validate Mermaid diagrams.",
                        severity="error",
                    )
                )
            except subprocess.CalledProcessError as e:
                stderr = (e.stderr or "").strip()
                stdout = (e.stdout or "").strip()
                combined = "\n".join([s for s in (stdout, stderr) if s]).strip()
                msg = "Mermaid render failed via mmdc."
                if combined:
                    # Prefer the first "Parse error" line if present; otherwise show last non-empty line.
                    parse_lines = [ln for ln in combined.splitlines() if "Parse error" in ln or "Error" in ln]
                    tail = (parse_lines[0] if parse_lines else combined.splitlines()[-1]).strip()
                    msg = f"{msg} {tail}"
                problems.append(
                    Problem(file=b.file, line=b.start_line, code="MERMAID001", message=msg, severity="error")
                )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Mermaid and ASCII art in Markdown for GitHub rendering.")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=["docs", "CLAUDE.md", "README.md", "backend/data/README.md"],
        help="Files/directories to scan (defaults to docs/ + key READMEs).",
    )
    parser.add_argument(
        "--max-code-line-len",
        type=int,
        default=160,
        help="Warn/fail on code-block lines longer than this.",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    scan_paths = [base / p for p in args.paths]
    md_files = _iter_markdown_files(scan_paths)

    all_mermaid: list[MermaidBlock] = []
    all_problems: list[Problem] = []

    for md in md_files:
        all_mermaid.extend(extract_mermaid_blocks(md))
        all_problems.extend(check_ascii_hygiene(md, max_code_line_len=args.max_code_line_len))

    all_problems.extend(render_mermaid_blocks(all_mermaid))

    errors = [p for p in all_problems if p.severity == "error"]
    warns = [p for p in all_problems if p.severity == "warn"]

    for p in errors + warns:
        rel = p.file.relative_to(base)
        print(f"{rel}:{p.line}: {p.severity.upper()} {p.code}: {p.message}")

    if errors:
        print(
            f"\nFAILED: {len(errors)} error(s), {len(warns)} warning(s) across {len(md_files)} Markdown files."
        )
        return 1

    if warns:
        print(f"\nOK (with warnings): {len(warns)} warning(s) across {len(md_files)} Markdown files.")
        return 0

    print(
        f"OK: Mermaid + ASCII checks passed for {len(md_files)} Markdown files. Mermaid blocks: {len(all_mermaid)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

