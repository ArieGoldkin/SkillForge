---
description: Create conventional commit with proper format
---

Create a commit for the current changes:

1. **Check status**: `git status` to see all changes
2. **Review diff**: `git diff` to understand what changed
3. **Check branch**: Verify NOT on dev/main (hooks will block anyway)
4. **Stage files**: `git add <relevant-files>` (avoid unrelated changes)
5. **Create commit** using conventional format:

   ```
   <type>(#<issue>): <description>

   [optional body]

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   Types:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation only
   - `refactor`: Code change that neither fixes bug nor adds feature
   - `test`: Adding or updating tests
   - `chore`: Build process, dependencies, tooling

6. **Verify**: `git log -1` to confirm commit message

Ask user if they want to push after committing.
