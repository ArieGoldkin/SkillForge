---
name: evidence-collection
description: Evidence collection protocol for task verification
version: 1.0.0
tags: [verification, evidence, quality, testing]
size: atomic
domain: process
---

# Evidence Collection

## Evidence Types

### Test Evidence
- Exit code (must be 0)
- Test results (passed/failed/skipped)
- Coverage percentage
- Duration

### Build Evidence
- Exit code (0 = success)
- Compilation errors/warnings
- Artifacts created
- Duration

### Code Quality Evidence
- Linter results
- Type checker results
- Security scan results

## Collection Protocol

```markdown
## Evidence Collection Steps

1. **Identify Verification Points**
   - What needs to be proven?
   - What could go wrong?

2. **Execute Verification**
   - Run tests
   - Run build
   - Run linters

3. **Capture Results**
   - Record exit codes
   - Save output snippets
   - Note timestamps

4. **Store Evidence**
   - Add to shared context
   - Reference in task completion
```

## Evidence Template

```markdown
## Task Completion Evidence

### Task: [Description]
### Completed: YYYY-MM-DD HH:MM:SS

### Verification Results

| Check | Command | Exit Code | Result |
|-------|---------|-----------|--------|
| Tests | `npm test` | 0 | ✅ 45 passed |
| Build | `npm run build` | 0 | ✅ Created |
| Linter | `npm run lint` | 0 | ✅ No errors |
| Types | `npm run typecheck` | 0 | ✅ Clean |

### Coverage
- Statements: 87%
- Branches: 82%
- Functions: 90%

### Conclusion
All checks passed. Ready for review.
```

## Quality Standards

**Minimum:**
- ✅ Tests executed with exit code
- ✅ Timestamp recorded
- ✅ Evidence stored in context

**Production-Grade:**
- ✅ Tests pass (exit 0)
- ✅ Coverage ≥70%
- ✅ Build succeeds
- ✅ No critical linter errors

## Anti-Patterns

```
❌ "Tests passed" (without running)
✅ "Tests: Exit 0, 45 passed, 87% coverage"

❌ "Build failed but code looks correct"
✅ "Build failed: [error]. Fixing before complete."
```
