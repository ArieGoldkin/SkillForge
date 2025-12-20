#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running docs consistency checks..."

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

# Files we consider “docs surface area” (avoid scanning tests, etc.)
TARGETS=(
  "README.md"
  "CLAUDE.md"
  "docs"
  "frontend/README.md"
  "backend/README.md"
)

echo "Verifying Mermaid + ASCII rendering (GitHub)..."
# Skip Mermaid rendering in CI (requires Chromium which isn't available in GitHub Actions)
if [ "${CI:-false}" = "true" ]; then
  echo "CI environment detected - skipping Mermaid rendering (requires Chromium)"
  python3 "scripts/verify_markdown_diagrams.py" --paths "${TARGETS[@]}" || true
else
  python3 "scripts/verify_markdown_diagrams.py" --paths "${TARGETS[@]}"
fi

rg_in_targets() {
  local pattern="$1"
  if command -v rg >/dev/null 2>&1; then
    rg --fixed-strings -n "$pattern" "${TARGETS[@]}" || true
    return 0
  fi

  # Fallback when ripgrep isn't installed locally.
  # -R: recursive
  # -n: line numbers
  # -F: fixed strings
  # --: end of options
  grep -R -n -F -- "$pattern" "${TARGETS[@]}" 2>/dev/null || true
}

# Guardrails to prevent drift we just fixed.
if rg_in_targets "localhost:8000" | grep -q .; then
  rg_in_targets "localhost:8000"
  fail "Found stale localhost:8000 references. Use docs/CONFIGURATION.md (source of truth) and update to localhost:8500."
fi

if rg_in_targets "VITE_API_BASE_URL" | grep -q .; then
  rg_in_targets "VITE_API_BASE_URL"
  fail "Found VITE_API_BASE_URL references. Use VITE_API_URL (see docs/CONFIGURATION.md)."
fi

if rg_in_targets "LangGraph 0.6.7" | grep -q .; then
  rg_in_targets "LangGraph 0.6.7"
  fail "Found LangGraph 0.6.7 references in docs surface area. Current backend uses LangGraph 1.0.4 (see backend/pyproject.toml)."
fi

echo "Docs consistency checks passed."


