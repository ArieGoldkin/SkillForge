---
description: Smart commit with validation and auto-generated message
---

# Create Commit

Intelligent commit creation with 2-3 parallel validation agents.

## Phase 1: Pre-Commit Safety Check

```bash
# CRITICAL: Verify we're not on dev/main
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" == "dev" || "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  echo "🛑 STOP! Cannot commit directly to $BRANCH"
  echo "Create a feature branch first:"
  echo "  git checkout -b issue/<number>-<description>"
  exit 1
fi

echo "✅ Branch OK: $BRANCH"
```

## Phase 2: Review Changes

```bash
# See what's changed
git status

# View the diff
git diff

# View staged changes
git diff --staged

# Show untracked files
git ls-files --others --exclude-standard
```

## Phase 3: Parallel Validation (2 Agents)

Launch TWO agents - BOTH in ONE message:

```python
# PARALLEL - Both in ONE message!

Task(
  subagent_type="code-quality-reviewer",
  prompt="""PRE-COMMIT VALIDATION

  Run quick validation on changed files:

  Backend (if changed):
  - poetry run ruff format --check app/
  - poetry run ruff check app/

  Frontend (if changed):
  - npm run format:check
  - npm run lint

  Check for:
  - No console.log/print statements
  - No hardcoded secrets
  - No TODO/FIXME without issue reference
  - No commented-out code blocks

  Output: Pass/fail with specific issues.""",
  run_in_background=true
)

Task(
  subagent_type="Explore",
  prompt="""COMMIT MESSAGE GENERATION

  Analyze the changes (git diff):
  1. What type of change? (feat/fix/refactor/docs/test/chore)
  2. What's the main purpose?
  3. What files are affected?
  4. Any issue references in branch name?

  Generate conventional commit message:
  - Subject line: <type>(#<issue>): <description>
  - Body: Bullet points of specific changes
  - Keep subject under 72 chars

  Output: Ready-to-use commit message.""",
  run_in_background=true
)
```

**Wait for both to complete.**

## Phase 4: Stage Files

```bash
# Stage specific files (recommended)
git add <specific-files>

# Or stage all changes (use carefully)
git add .

# Interactive staging
# git add -p  # Not supported in Claude
```

## Phase 5: Create Commit

```bash
# Use generated message with proper format
git commit -m "$(cat <<'EOF'
<type>(#<issue>): <brief description>

- [Specific change 1]
- [Specific change 2]
- [Specific change 3]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Verify commit
git log -1 --stat
```

## Commit Types Reference

| Type | When to Use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(#123): Add user authentication` |
| `fix` | Bug fix | `fix(#456): Resolve login timeout` |
| `refactor` | Code improvement | `refactor: Simplify auth service` |
| `docs` | Documentation | `docs: Update API documentation` |
| `test` | Tests only | `test: Add unit tests for auth` |
| `chore` | Build/deps/tooling | `chore: Update dependencies` |
| `perf` | Performance | `perf: Optimize database queries` |
| `style` | Formatting | `style: Fix linting issues` |

## Phase 6: Post-Commit Actions

```bash
# Show commit summary
echo "✅ Commit created successfully!"
git log -1 --oneline

# Check if ready to push
echo ""
echo "📤 Ready to push? Run:"
echo "   git push -u origin $BRANCH"
echo ""
echo "📝 Ready for PR? Run:"
echo "   /create-pr"
```

## Quick Commit (No Agents)

For simple, obvious changes:

```bash
# Check branch first!
git branch --show-current

# Quick commit
git add .
git commit -m "fix(#123): Fix typo in readme

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Summary

**Total Parallel Agents: 2**
- 1 code-quality-reviewer (validation)
- 1 Explore (message generation)

**Safety Checks:**
- ❌ Block commits to dev/main/master
- ✅ Lint validation before commit
- ✅ No secrets in changes
- ✅ Conventional commit format

**Commit Message Format:**
```
<type>(#<issue>): <subject line - max 72 chars>

- [Change 1]
- [Change 2]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Best Practices:**
- One logical change per commit
- Reference issue numbers
- Write meaningful descriptions
- Keep subject line concise
- Use body for details

**Recovery if Committed to Wrong Branch:**
```bash
# Save work to new branch
git checkout -b issue/<number>-<description>

# Reset original branch
git checkout dev
git reset --hard origin/dev

# Continue on feature branch
git checkout issue/<number>-<description>
git push -u origin issue/<number>-<description>
```
