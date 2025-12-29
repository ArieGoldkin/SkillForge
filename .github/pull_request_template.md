## Description
<!-- Provide a clear and concise description of your changes -->



## Type of Change
<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] 🧪 Test improvements

## Related Issue
<!--
IMPORTANT: Use GitHub auto-close syntax to link issues:
- "Fixes #123" - Auto-closes issue when PR merges to default branch
- "Closes #123" - Same as Fixes
- "Resolves #123" - Same as Fixes
Multiple issues: "Fixes #123, Fixes #456"

DO NOT write just "#123" or "Related to #123" - the issue won't auto-close!
-->

Fixes #

## Changes Made
<!-- List the main changes in bullet points -->

-
-
-

## Testing
<!-- Describe how you tested your changes -->

### Test Plan
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

### Testing Details
<!-- Describe your testing approach -->



## Screenshots (if applicable)
<!-- Add screenshots or screen recordings to demonstrate changes -->



## Checklist
<!-- Mark completed items with an 'x' - ALL must be checked before requesting review -->

### Code Quality
- [ ] I have used the correct auto-close syntax (`Fixes #123`) in the Related Issue section above
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors

### Testing (MUST run locally before PR)
- [ ] Backend: `cd backend && poetry run pytest tests/unit/ -v --tb=short` passes
- [ ] Backend: `cd backend && poetry run ruff format --check app/ && poetry run ruff check app/` passes
- [ ] Backend: `cd backend && poetry run ty check app/ --exclude "app/evaluation/*"` passes
- [ ] Frontend: `cd frontend && npm run format:check && npm run lint && npm run typecheck` passes
- [ ] I have added tests that prove my fix is effective or that my feature works

### Documentation
- [ ] I have made corresponding changes to the documentation
- [ ] Any dependent changes have been merged and published

## Additional Notes
<!-- Add any additional notes for reviewers -->


