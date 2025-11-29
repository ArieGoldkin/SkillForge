# Frontend Dependency Upgrade Plan

**Date:** 2025-11-29
**Objective:** Systematically upgrade all Dependabot PRs with minimal risk

---

## Upgrade Strategy

### Batch 1: Zero-Risk Patches (merge all)
| Package | Change | Verification |
|---------|--------|--------------|
| lucide-react | 0.554.0 → 0.555.0 | `npm run build` |
| @types/react | 19.2.5 → 19.2.7 | `tsc --noEmit` |
| @tanstack/react-query | 5.90.10 → 5.90.11 | `npm test` |
| @tanstack/react-router | 1.139.3 → 1.139.10 | `npm run dev` (navigate routes) |

**Action:** Merge all 4 PRs, run verification once.

### Batch 2: Dev Tooling
| Package | Change | Code Impact |
|---------|--------|-------------|
| @biomejs/biome | 2.3.7 → 2.3.8 | Run `npm run format` after |
| typescript-eslint | 8.46.4 → 8.48.0 | None required |

**Action:** Merge both, run `npm run format && npm run lint`.

### Batch 3: CI/CD (test separately)
| Package | Change | Risk |
|---------|--------|------|
| actions/upload-artifact | v4 → v5 | Medium - test in PR |

**Action:** Create test PR, verify CI passes before merge.

---

## Execution Commands

```bash
# Step 1: Merge Batch 1 (runtime deps - zero risk)
gh pr merge 102 --squash --delete-branch  # lucide-react 0.555.0
gh pr merge 97  --squash --delete-branch  # @types/react 19.2.7
gh pr merge 106 --squash --delete-branch  # react-query 5.90.11
gh pr merge 100 --squash --delete-branch  # react-router 1.139.10

# Step 2: Sync and verify
git pull origin dev
cd frontend && npm install
npm run build && npm test

# Step 3: Merge Batch 2 (dev tools)
gh pr merge 104 --squash --delete-branch  # biome 2.3.8
gh pr merge 101 --squash --delete-branch  # typescript-eslint 8.48.0
gh pr merge 98  --squash --delete-branch  # dev-dependencies group

# Step 4: Verify + format
git pull origin dev
cd frontend && npm install
npm run format && npm run lint && npm run build

# Step 5: Merge CI/CD (after CI passes)
gh pr merge 54 --squash --delete-branch  # upload-artifact v5
```

---

## Codebase Changes Required

### None for Batch 1 & 2
All are backward-compatible patches. No code changes needed.

### Optional: Enable New ESLint Rule
After typescript-eslint upgrade, can add to `eslint.config.js`:
```javascript
'@typescript-eslint/no-unnecessary-template-expression': 'warn'
```

---

## Rollback Plan

If any issues:
```bash
git revert HEAD~N  # N = number of merged commits
npm install
```

---

## Timeline

| Batch | Time | Blocker |
|-------|------|---------|
| Batch 1 | 5 min | None |
| Batch 2 | 5 min | None |
| Batch 3 | 15 min | CI must pass |

**Total: ~25 minutes**
