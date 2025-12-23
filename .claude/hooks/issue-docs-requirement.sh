#!/bin/bash
# Issue Documentation Requirement Hook for Claude Code
# Ensures docs/issues/<issue-num>-*/README.md exists before creating issue branches
# Exit code 2 blocks the command; exit code 0 allows it

set -o pipefail

# Read hook input from stdin
INPUT=$(cat)

# Extract the bash command
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Only check for git checkout -b commands creating issue branches
if [[ ! "$COMMAND" =~ git\ checkout\ -b\ issue/ ]]; then
  # Not creating an issue branch, allow it
  exit 0
fi

# Extract branch name from command
# Handles: git checkout -b issue/489-description
BRANCH_NAME=$(echo "$COMMAND" | grep -oE 'issue/[0-9]+-[a-zA-Z0-9_-]+' | head -1)

if [[ -z "$BRANCH_NAME" ]]; then
  # Couldn't parse branch name, allow command (might be different format)
  exit 0
fi

# Extract issue number from branch name
ISSUE_NUM=$(echo "$BRANCH_NAME" | grep -oE '[0-9]+' | head -1)

if [[ -z "$ISSUE_NUM" ]]; then
  # No issue number found, allow command
  exit 0
fi

# Check if docs/issues/<issue-num>-*/README.md exists
DOCS_PATH="$CLAUDE_PROJECT_DIR/docs/issues"
MATCHING_DOCS=$(find "$DOCS_PATH" -maxdepth 2 -type f -name "README.md" -path "*/${ISSUE_NUM}-*/*" 2>/dev/null | head -1)

if [[ -n "$MATCHING_DOCS" ]]; then
  # Documentation exists, allow branch creation
  exit 0
fi

# Documentation missing - block and show instructions
TEMPLATE_PATH="$CLAUDE_PROJECT_DIR/.claude/templates/issue-readme.md"

cat >&2 << EOF
╔══════════════════════════════════════════════════════════════════════════════╗
║  BLOCKED: Issue documentation required before starting work                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Branch:   $BRANCH_NAME
Issue #:  $ISSUE_NUM

Required: Create docs/issues/${ISSUE_NUM}-<description>/README.md first.

Steps:
  1. mkdir -p docs/issues/${ISSUE_NUM}-<description>
  2. Create README.md with the template below
  3. Retry: git checkout -b $BRANCH_NAME

EOF

# Show template if it exists, otherwise show inline template
if [[ -f "$TEMPLATE_PATH" ]]; then
  echo "Template (from .claude/templates/issue-readme.md):" >&2
  echo "────────────────────────────────────────────────────────────────────────" >&2
  sed "s/{{ISSUE_NUM}}/${ISSUE_NUM}/g" "$TEMPLATE_PATH" >&2
else
  cat >&2 << 'TEMPLATE'
Template structure:
────────────────────────────────────────────────────────────────────────────
# Issue #<NUM>: <Title from GitHub>

## Summary
<1-2 sentences: What is the problem?>

## Evidence
<Logs, screenshots, DB queries, error messages>

## Root Cause Analysis
<Why does this happen? Include diagrams if helpful>

## Solution Approach
<High-level strategy: which approach and why>

## Implementation Phases
| Phase | Description | Files |
|-------|-------------|-------|
| 1 | ... | ... |
| 2 | ... | ... |

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
- [ ] Lint checks pass

## Related Files
- `path/to/file.ts` - Description of changes needed
────────────────────────────────────────────────────────────────────────────
TEMPLATE
fi

echo "" >&2
echo "Why? Documentation-first ensures you understand the problem before coding." >&2

exit 2
