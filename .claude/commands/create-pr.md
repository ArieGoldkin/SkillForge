---
description: Create pull request to dev branch
---

Create a PR for the current branch:

1. **Check branch**: `git branch --show-current` (must NOT be dev/main)
2. **Check status**: `git status` (should be clean or staged)
3. **Push branch**: `git push -u origin HEAD`
4. **Get commits**: `git log --oneline dev..HEAD` to summarize changes
5. **Create PR**:

```bash
gh pr create --base dev --title "<type>(#<issue>): <description>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points of what this PR does>

## Changes
- [ ] Change 1
- [ ] Change 2

## Test Plan
- [ ] Unit tests pass
- [ ] Manual testing done

## Related Issues
Closes #<issue-number>

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

6. **Verify**: `gh pr view --web` to open in browser

PR title format: `<type>(#<issue>): <short description>`
- feat, fix, docs, refactor, test, chore
