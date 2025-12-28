---
description: Create PR with parallel validation and auto-generated description
---

# Create Pull Request

Comprehensive PR creation with 3-4 parallel agents for validation and description generation.

## Phase 1: Pre-Flight Checks

```bash
# Verify branch
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" == "dev" || "$BRANCH" == "main" ]]; then
  echo "❌ Cannot create PR from dev/main. Create a feature branch first."
  exit 1
fi

# Check for uncommitted changes
git status --porcelain
if [[ -n $(git status --porcelain) ]]; then
  echo "⚠️ Uncommitted changes detected. Commit or stash first."
fi

# Check if branch is pushed
git fetch origin
if ! git rev-parse --verify origin/$BRANCH &>/dev/null; then
  echo "📤 Branch not pushed. Pushing now..."
  git push -u origin $BRANCH
fi
```

## Phase 2: Gather PR Context

```bash
# Get all commits in this branch
git log --oneline dev..HEAD

# Get full diff from dev
git diff dev...HEAD --stat

# Get changed files
git diff --name-only dev...HEAD
```

## Phase 3: Parallel Validation & Analysis (4 Agents)

Launch FOUR agents - ALL in ONE message:

```python
# PARALLEL - All four in ONE message!

Task(
  subagent_type="code-quality-reviewer",
  prompt="""PRE-PR VALIDATION

  Run all validation checks:

  Backend:
  - cd backend && poetry run ruff format --check app/
  - cd backend && poetry run ruff check app/
  - cd backend && poetry run ty check app/ --exclude "app/evaluation/*"
  - cd backend && poetry run pytest tests/unit/ -v --tb=short

  Frontend:
  - cd frontend && npm run format:check
  - cd frontend && npm run lint
  - cd frontend && npm run typecheck
  - cd frontend && npm run test

  Report: Pass/fail status for each check.""",
  run_in_background=true
)

Task(
  subagent_type="Explore",
  prompt="""CHANGE ANALYSIS

  Analyze all changes in this branch:
  - git diff dev...HEAD

  Identify:
  1. What features/fixes are included?
  2. Which components are affected?
  3. Any breaking changes?
  4. Database migrations?
  5. New dependencies?

  Output: Structured change summary.""",
  run_in_background=true
)

Task(
  subagent_type="product-manager",
  prompt="""PR DESCRIPTION GENERATION

  Based on commits and changes, generate:

  1. **Summary**: 1-2 sentences explaining what this PR does
  2. **Changes**: Bullet list of specific changes
  3. **Type**: feat/fix/refactor/docs/test/chore
  4. **Breaking Changes**: Any? If so, what?
  5. **Related Issues**: Extract from commit messages

  Format for GitHub PR body.""",
  run_in_background=true
)

Task(
  subagent_type="code-quality-reviewer",
  prompt="""TEST PLAN GENERATION

  Based on the changes, create test plan:

  1. What manual testing should reviewers do?
  2. What automated tests cover these changes?
  3. Edge cases to verify
  4. Regression concerns

  Format as checklist for PR body.""",
  run_in_background=true
)
```

**Wait for all 4 to complete.**

## Phase 4: Extract Issue Reference

```bash
# Try to extract issue number from branch name
ISSUE=$(echo $BRANCH | grep -oE '[0-9]+' | head -1)

# Or from commit messages
if [[ -z "$ISSUE" ]]; then
  ISSUE=$(git log --oneline dev..HEAD | grep -oE '#[0-9]+' | head -1 | tr -d '#')
fi
```

## Phase 5: Create PR

```bash
# Determine PR type from changes
TYPE="feat"  # or fix, refactor, docs, test, chore

# Create PR with generated description
gh pr create --base dev --title "$TYPE(#$ISSUE): [Brief description from analysis]" --body "$(cat <<'EOF'
## Summary
[Generated summary from product-manager agent]

## Changes
- [Change 1]
- [Change 2]
- [Change 3]

## Type
- [x] Feature (new functionality)
- [ ] Bug fix (fixes an issue)
- [ ] Refactor (code improvement, no functional change)
- [ ] Documentation
- [ ] Test (adding or updating tests)
- [ ] Chore (build, CI, dependencies)

## Breaking Changes
- [ ] No breaking changes
- [ ] Breaking changes (describe below)

[If breaking, explain migration steps]

## Related Issues
- Closes #$ISSUE

## Test Plan
### Automated Tests
- [x] Unit tests pass
- [x] Lint/type checks pass
- [x] Coverage maintained

### Manual Testing
- [ ] [Test scenario 1]
- [ ] [Test scenario 2]
- [ ] [Edge case to verify]

## Screenshots (if UI changes)
[Add screenshots if applicable]

## Checklist
- [x] Code follows project style guidelines
- [x] Self-reviewed the code
- [x] Added/updated tests
- [x] Documentation updated (if needed)
- [x] No console.log/print statements left

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

# Open PR in browser
gh pr view --web
```

## Phase 6: Post-PR Actions

```bash
# Get PR number
PR_NUMBER=$(gh pr view --json number -q .number)

echo "✅ PR #$PR_NUMBER created successfully!"
echo "🔗 URL: $(gh pr view --json url -q .url)"

# Optional: Add labels
gh pr edit $PR_NUMBER --add-label "needs-review"

# Optional: Request reviewers
# gh pr edit $PR_NUMBER --add-reviewer @username
```

## Phase 7: Save Context

```python
mcp__memory__create_entities(entities=[{
  "name": "pr-[branch]-[date]",
  "entityType": "pull-request",
  "observations": [
    "Branch: [branch]",
    "PR: #[number]",
    "Changes: [summary]",
    "Status: open"
  ]
}])
```

---

## Summary

**Total Parallel Agents: 4**
- 2 code-quality-reviewer (validation, test plan)
- 1 Explore (change analysis)
- 1 product-manager (PR description)

**MCPs Used:**
- 💾 memory (save PR context)

**PR Template Sections:**
- Summary (auto-generated)
- Changes list (auto-generated)
- Type classification
- Breaking changes indicator
- Related issues (auto-extracted)
- Test plan (auto-generated)
- Manual testing checklist
- Standard checklist

**Branch Naming Convention:**
- `issue/<number>-<description>` - GitHub issues
- `feature/<description>` - New features
- `fix/<description>` - Bug fixes

**Commit Message Format:**
```
<type>(#<issue>): <description>

[body]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```
