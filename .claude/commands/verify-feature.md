---
description: Comprehensive feature verification before merge
---

Verify feature branch: $ARGUMENTS (default: current branch)

## Step 1: Branch Context

```bash
# Current branch and commits
git branch --show-current
git log --oneline dev..HEAD

# Files changed vs dev
git diff --stat dev...HEAD

# Check if up to date with dev
git fetch origin dev
git log HEAD..origin/dev --oneline
```

## Step 2: Run All CI Checks Locally

```bash
# Backend
cd backend
poetry run ruff format --check app/
poetry run ruff check app/
poetry run ty check app/ --exclude "app/evaluation/*"
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tee /tmp/test_results.log

# Frontend
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test 2>&1 | tee /tmp/frontend_test_results.log
```

## Step 3: Feature-Specific Testing

Based on changed files, run targeted tests:
```bash
# Find test files related to changed files
git diff --name-only dev...HEAD | grep -E "\.py$" | \
  xargs -I{} basename {} .py | \
  xargs -I{} find tests/ -name "*{}*"
```

## Step 4: Visual Verification (if UI changes)

Use Playwright to capture screenshots:
```python
mcp__playwright__browser_navigate(url="http://localhost:5173")
mcp__playwright__browser_take_screenshot(filename="feature-verification.png")
```

Or ask user to verify in browser and use Chrome extension to capture.

## Step 5: Code Quality Review

```python
Task(
  subagent_type="code-quality-reviewer",
  prompt="""Review all changes in this feature branch:

  git diff dev...HEAD

  Check for:
  - Security issues (secrets, injection, XSS)
  - Performance problems (N+1 queries, memory leaks)
  - Test coverage (new code has tests)
  - Type safety (no 'any', proper typing)
  - Error handling (appropriate try/catch)
  """
)
```

## Step 6: Generate Verification Report

```markdown
## Feature Verification Report

**Branch**: [branch-name]
**Commits**: [count] commits ahead of dev
**Files Changed**: [count]

### CI Checks
- [ ] Backend format: ✅/❌
- [ ] Backend lint: ✅/❌
- [ ] Backend types: ✅/❌
- [ ] Backend tests: ✅/❌ ([passed]/[total])
- [ ] Frontend format: ✅/❌
- [ ] Frontend lint: ✅/❌
- [ ] Frontend types: ✅/❌
- [ ] Frontend tests: ✅/❌

### Manual Verification
- [ ] Feature works as expected
- [ ] No console errors
- [ ] No visual regressions

### Ready for Merge
- [ ] All checks pass
- [ ] Code reviewed
- [ ] Tests cover new functionality
```

## Step 7: Create/Update PR

If all checks pass:
```bash
gh pr create --base dev --title "..." --body "..."
# or update existing
gh pr edit --body "..."
```
