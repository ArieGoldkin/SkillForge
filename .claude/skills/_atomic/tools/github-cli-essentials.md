---
name: github-cli-essentials
description: Essential gh CLI commands for issues, PRs, and projects
version: 1.0.0
tags: [github, gh, cli, issues, pr]
size: atomic
domain: tools
---

# GitHub CLI Essentials

## Issue Operations

```bash
# Create issue
gh issue create --title "feat: Add caching" \
  --body "Description here" \
  --label "enhancement" \
  --milestone "Sprint 1"

# List issues
gh issue list --state open --label "backend" --assignee @me

# Edit issue
gh issue edit 123 --add-label "high" --milestone "v2.0"

# View issue
gh issue view 123
```

## PR Operations

```bash
# Create PR
gh pr create --title "feat(#123): Add caching" \
  --body "Closes #123" \
  --base dev \
  --reviewer @teammate

# Watch CI status
gh pr checks 456 --watch

# Merge PR
gh pr merge 456 --squash --delete-branch

# Auto-merge when approved
gh pr merge 456 --auto --squash
```

## JSON Output + jq

```bash
# Get issue numbers by label
gh issue list --json number,labels \
  --jq '[.[] | select(.labels[].name == "bug")] | .[].number'

# PR summary
gh pr list --json number,title,author \
  --jq '.[] | "\(.number): \(.title) by \(.author.login)"'

# Count open PRs
gh pr list --json state --jq 'length'
```

## Branch Naming

```bash
issue/<number>-<description>   # For issues
feature/<description>          # Without issue
fix/<description>              # Bug fixes

# Examples:
issue/372-langfuse-migration
feature/add-caching
fix/null-pointer
```

## Commit Message Format

```bash
# type(#issue): description
feat(#372): Implement Langfuse tracing
fix(#345): Resolve null pointer bug
docs(#336): Update API documentation
refactor(#391): Extract validation logic
```

## Best Practices

- ✅ Use `--json` for scripting
- ✅ Use heredocs for multi-line body
- ✅ Link issues in PRs: `Closes #123`
- ✅ Never commit to main directly
