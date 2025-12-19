# GitHub Issue Creation Commands

Run these commands from the SkillForge root directory to create all 7 high-priority frontend issues.

## Prerequisites

Ensure you have GitHub CLI installed and authenticated:
```bash
gh auth status
```

If not authenticated:
```bash
gh auth login
```

## Issue Creation Commands

### Issue #6: Excessive Re-Renders
```bash
gh issue create \
  --title "🟠 HIGH: Excessive Re-Renders - 1,600+ Component Updates Per Analysis" \
  --label "high-priority,frontend,performance,bug" \
  --body-file .github/issue-templates/issue-06-excessive-rerenders.md
```

### Issue #7: Prop Drilling Hell
```bash
gh issue create \
  --title "🟠 HIGH: Prop Drilling Hell - 15+ Interface Definitions" \
  --label "high-priority,frontend,refactor,technical-debt" \
  --body-file .github/issue-templates/issue-07-prop-drilling.md
```

### Issue #8: Code Duplication
```bash
gh issue create \
  --title "🟠 HIGH: Code Duplication - 661 Lines Across 3 Stage Config Files" \
  --label "high-priority,frontend,refactor,technical-debt" \
  --body-file .github/issue-templates/issue-08-code-duplication.md
```

### Issue #9: Unsafe Type Assertions
```bash
gh issue create \
  --title "🟠 HIGH: Unsafe Type Assertions - 24 'as any' in Tests" \
  --label "high-priority,frontend,testing,type-safety,technical-debt" \
  --body-file .github/issue-templates/issue-09-unsafe-type-assertions.md
```

### Issue #10: Missing Loading States
```bash
gh issue create \
  --title "🟠 HIGH: Missing Loading States - Single State for Complex Flow" \
  --label "high-priority,frontend,enhancement,ux" \
  --body-file .github/issue-templates/issue-10-missing-loading-states.md
```

### Issue #11: Complex Conditional Rendering
```bash
gh issue create \
  --title "🟠 HIGH: Complex Conditional Rendering - 7 Levels of Nested Ifs" \
  --label "high-priority,frontend,refactor,technical-debt" \
  --body-file .github/issue-templates/issue-11-complex-conditional-rendering.md
```

### Issue #12: No Performance Monitoring
```bash
gh issue create \
  --title "🟠 HIGH: No Performance Monitoring - Zero Visibility" \
  --label "high-priority,frontend,performance,observability,enhancement" \
  --body-file .github/issue-templates/issue-12-no-performance-monitoring.md
```

## Bulk Creation (All at Once)

If you want to create all issues at once, run this script:

```bash
#!/bin/bash

ISSUES=(
  "issue-06-excessive-rerenders.md|🟠 HIGH: Excessive Re-Renders - 1,600+ Component Updates Per Analysis|high-priority,frontend,performance,bug"
  "issue-07-prop-drilling.md|🟠 HIGH: Prop Drilling Hell - 15+ Interface Definitions|high-priority,frontend,refactor,technical-debt"
  "issue-08-code-duplication.md|🟠 HIGH: Code Duplication - 661 Lines Across 3 Stage Config Files|high-priority,frontend,refactor,technical-debt"
  "issue-09-unsafe-type-assertions.md|🟠 HIGH: Unsafe Type Assertions - 24 'as any' in Tests|high-priority,frontend,testing,type-safety,technical-debt"
  "issue-10-missing-loading-states.md|🟠 HIGH: Missing Loading States - Single State for Complex Flow|high-priority,frontend,enhancement,ux"
  "issue-11-complex-conditional-rendering.md|🟠 HIGH: Complex Conditional Rendering - 7 Levels of Nested Ifs|high-priority,frontend,refactor,technical-debt"
  "issue-12-no-performance-monitoring.md|🟠 HIGH: No Performance Monitoring - Zero Visibility|high-priority,frontend,performance,observability,enhancement"
)

for issue in "${ISSUES[@]}"; do
  IFS='|' read -r file title labels <<< "$issue"
  echo "Creating issue: $title"
  gh issue create \
    --title "$title" \
    --label "$labels" \
    --body-file ".github/issue-templates/$file"
  sleep 2 # Rate limiting
done

echo "✅ All issues created successfully!"
```

Save this as `create-all-issues.sh`, make it executable, and run:
```bash
chmod +x create-all-issues.sh
./create-all-issues.sh
```

## Verification

After creating the issues, verify with:
```bash
gh issue list --label "high-priority,frontend"
```

## Issue Summary

| # | Title | Priority | Category | Est. Hours |
|---|-------|----------|----------|-----------|
| 6 | Excessive Re-Renders | HIGH | Performance | 6-8 |
| 7 | Prop Drilling Hell | HIGH | Architecture | 5-7 |
| 8 | Code Duplication | HIGH | Technical Debt | 5-7 |
| 9 | Unsafe Type Assertions | HIGH | Type Safety | 6-9 |
| 10 | Missing Loading States | HIGH | UX | 6-8 |
| 11 | Complex Conditional Rendering | HIGH | Architecture | 3-6 |
| 12 | No Performance Monitoring | HIGH | Observability | 10-15 |

**Total estimated effort:** 41-60 hours

## Related Documentation

- Frontend analysis: `docs/frontend-analysis/analysis-features-analysis.md`
- Original assessment: See product manager's analysis
- Architecture decisions: `.claude/instructions/architecture-decisions.md`
