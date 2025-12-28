---
description: Review pull request for quality and issues
---

Review PR #$ARGUMENTS:

1. **Get PR info**: `gh pr view $ARGUMENTS --json title,body,files,additions,deletions`
2. **View changes**: `gh pr diff $ARGUMENTS`
3. **Check CI status**: `gh pr checks $ARGUMENTS`

Review checklist:
- [ ] **Code quality**: Clean, readable, follows project patterns
- [ ] **Tests**: Changes are tested, tests pass
- [ ] **Security**: No hardcoded secrets, SQL injection, XSS
- [ ] **Performance**: No obvious N+1 queries, memory leaks
- [ ] **Types**: Proper TypeScript/Python typing
- [ ] **Error handling**: Appropriate try/catch, error messages

Provide structured feedback:
```markdown
## Summary
[1-2 sentence overview]

## ✅ Strengths
- [What's done well]

## ⚠️ Suggestions
- [Non-blocking improvements]

## 🔴 Blockers (if any)
- [Must-fix issues]
```

If approved: `gh pr review $ARGUMENTS --approve -b "LGTM! [brief comment]"`
If changes needed: `gh pr review $ARGUMENTS --request-changes -b "[feedback]"`
