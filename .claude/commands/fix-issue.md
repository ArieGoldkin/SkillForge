---
description: Fix GitHub issue by number
---

Fix GitHub issue #$ARGUMENTS:

1. **Get issue details**: `gh issue view $ARGUMENTS --json title,body,labels,assignees`
2. **Understand the problem**: Read the issue description and any linked files
3. **Search codebase**: Find relevant files using Grep/Glob
4. **Implement the fix**: Make minimal, focused changes
5. **Add/update tests**: Ensure the fix is tested
6. **Run checks**:
   - Backend: `cd backend && poetry run pytest tests/unit/ -v --tb=short`
   - Backend lint: `cd backend && poetry run ruff format --check app/ && poetry run ruff check app/`
   - Frontend: `cd frontend && npm run lint && npm run typecheck`
7. **Create commit**: `git commit -m "fix(#$ARGUMENTS): <description>"`
8. **Push and create PR**: `git push -u origin HEAD && gh pr create --base dev`

Remember:
- Create feature branch first if on dev/main
- Include issue reference in commit message
- Keep changes focused on the issue
