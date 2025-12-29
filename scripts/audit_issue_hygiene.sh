#!/bin/bash
# SkillForge Issue Hygiene Audit Script
# Identifies issues referenced in commits that may be completed but remain open
#
# Usage:
#   ./scripts/audit_issue_hygiene.sh                    # Default: last 6 months
#   MONTHS_BACK=12 ./scripts/audit_issue_hygiene.sh     # Custom time period
#   OUTPUT_FILE=custom.md ./scripts/audit_issue_hygiene.sh  # Custom output
#
# Environment Variables:
#   REPO         - GitHub repository (default: ArieGoldkin/SkillForge)
#   MONTHS_BACK  - Months of history to analyze (default: 6)
#   OUTPUT_FILE  - Output file path (default: issue_hygiene_report.md)

set -e

# Configuration
REPO="${REPO:-ArieGoldkin/SkillForge}"
MONTHS_BACK="${MONTHS_BACK:-6}"
OUTPUT_FILE="${OUTPUT_FILE:-issue_hygiene_report.md}"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
  echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
  echo ""
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
  if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    exit 1
  fi

  if ! command -v jq &> /dev/null; then
    print_error "jq is not installed"
    echo "Install it with: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
  fi

  if ! git rev-parse --git-dir &> /dev/null; then
    print_error "Not in a git repository"
    exit 1
  fi

  # Check gh authentication
  if ! gh auth status &> /dev/null; then
    print_error "GitHub CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
  fi
}

# Main audit function
run_audit() {
  print_header "Issue Hygiene Audit - $(date +%Y-%m-%d)"

  # Calculate date threshold
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    MONTHS_AGO=$(date -v-${MONTHS_BACK}m +%Y-%m-%d)
  else
    # Linux
    MONTHS_AGO=$(date -d "$MONTHS_BACK months ago" +%Y-%m-%d)
  fi

  print_info "Analyzing commits since: $MONTHS_AGO"
  print_info "Repository: $REPO"
  echo ""

  # Create report header
  cat << EOF > "$OUTPUT_FILE"
# 🧹 Issue Hygiene Audit Report

**Generated:** $(date +%Y-%m-%d)
**Repository:** $REPO
**Analysis Period:** Last $MONTHS_BACK months

## Summary

This report identifies GitHub issues that may be completed but remain open, based on commit references.

EOF

  # Extract issue references from git log
  echo "📋 Scanning commit history for issue references..."
  ISSUE_REFS=$(git log --since="$MONTHS_AGO" --all --oneline --grep='#[0-9]\+' | \
    grep -oE '#[0-9]+' | sed 's/#//' | sort -u)

  if [ -z "$ISSUE_REFS" ]; then
    print_warning "No issue references found in commits"
    cat << EOF >> "$OUTPUT_FILE"

**No issue references found in recent commits (last $MONTHS_BACK months).**

This could indicate:
- Issues are not being referenced in commits
- All referenced issues have been closed
- Consider using conventional commit messages with issue references

EOF
    print_success "Report saved to: $OUTPUT_FILE"
    return
  fi

  TOTAL_REFS=$(echo "$ISSUE_REFS" | wc -l | tr -d ' ')
  print_info "Found $TOTAL_REFS unique issue references"
  echo ""

  # Initialize counters
  OPEN_ISSUES=""
  CLOSED_ISSUES=0
  NOT_FOUND=0
  CURRENT=0

  # Create progress bar function
  show_progress() {
    local current=$1
    local total=$2
    local percent=$((current * 100 / total))
    local filled=$((current * 50 / total))
    local empty=$((50 - filled))

    printf "\r${BLUE}Progress: [${NC}"
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "${BLUE}] %d%% (%d/%d)${NC}" "$percent" "$current" "$total"
  }

  echo "🔍 Cross-referencing with GitHub API..."

  # Process each issue
  while IFS= read -r ISSUE_NUM; do
    ((CURRENT++))
    show_progress $CURRENT $TOTAL_REFS

    # Fetch issue data from GitHub API
    ISSUE_DATA=$(gh api repos/$REPO/issues/$ISSUE_NUM 2>/dev/null || echo "")

    if [ -z "$ISSUE_DATA" ]; then
      ((NOT_FOUND++))
      continue
    fi

    STATE=$(echo "$ISSUE_DATA" | jq -r '.state')

    if [ "$STATE" = "open" ]; then
      TITLE=$(echo "$ISSUE_DATA" | jq -r '.title')
      UPDATED=$(echo "$ISSUE_DATA" | jq -r '.updated_at' | cut -d'T' -f1)
      LABELS=$(echo "$ISSUE_DATA" | jq -r '.labels | map(.name) | join(", ")')
      [ -z "$LABELS" ] && LABELS="none"
      ASSIGNEE=$(echo "$ISSUE_DATA" | jq -r '.assignee.login // "unassigned"')

      # Count commits referencing this issue
      COMMIT_COUNT=$(git log --since="$MONTHS_AGO" --all --oneline --grep="#$ISSUE_NUM" | wc -l | tr -d ' ')

      # Escape pipe characters in title
      TITLE_ESCAPED=$(echo "$TITLE" | sed 's/|/\\|/g')

      OPEN_ISSUES="${OPEN_ISSUES}| [#$ISSUE_NUM](https://github.com/$REPO/issues/$ISSUE_NUM) | $TITLE_ESCAPED | $COMMIT_COUNT | $UPDATED | @$ASSIGNEE | $LABELS |
"
    else
      ((CLOSED_ISSUES++))
    fi
  done <<< "$ISSUE_REFS"

  echo ""  # New line after progress bar
  echo ""

  OPEN_COUNT=$(echo "$OPEN_ISSUES" | grep -c '|' || echo 0)

  # Write statistics
  cat << EOF >> "$OUTPUT_FILE"

### Statistics

- **Total Unique Issues Referenced**: $TOTAL_REFS
- **Currently Open**: $OPEN_COUNT
- **Already Closed**: $CLOSED_ISSUES
- **Not Found** (deleted/invalid): $NOT_FOUND

EOF

  # Write findings
  if [ "$OPEN_COUNT" -gt 0 ]; then
    print_warning "Found $OPEN_COUNT open issues with recent commits"

    cat << EOF >> "$OUTPUT_FILE"

## 🔍 Open Issues with Recent Commits

These issues have been referenced in commits but remain open. Consider reviewing for closure:

| Issue | Title | Commits | Last Updated | Assignee | Labels |
|-------|-------|---------|--------------|----------|--------|
$OPEN_ISSUES

### Recommended Actions

1. **Review each issue** to determine if work is complete
2. **Close completed issues** with appropriate comments
3. **Update labels** if work is still in progress
4. **Add missing commits** if issue references were forgotten

### Investigation Tips

To see commits for a specific issue:
\`\`\`bash
git log --all --oneline --grep="#ISSUE_NUMBER"
\`\`\`

To view full issue details:
\`\`\`bash
gh issue view ISSUE_NUMBER
\`\`\`

To close an issue:
\`\`\`bash
gh issue close ISSUE_NUMBER --comment "Closing as work is complete"
\`\`\`

EOF

    # Print top issues to console
    echo "Top issues to review:"
    echo "$OPEN_ISSUES" | head -6 | tail -5 | while IFS='|' read -r _ issue title commits _ _ _; do
      issue_clean=$(echo "$issue" | sed 's/\[//g' | sed 's/\].*//g' | tr -d ' ')
      title_clean=$(echo "$title" | sed 's/^ *//g' | sed 's/ *$//g')
      commits_clean=$(echo "$commits" | tr -d ' ')
      printf "  ${YELLOW}%-8s${NC} %s ${BLUE}(%s commits)${NC}\n" "$issue_clean" "$title_clean" "$commits_clean"
    done
  else
    print_success "All clear! All referenced issues are closed"

    cat << EOF >> "$OUTPUT_FILE"

## ✅ All Clear!

All issues referenced in recent commits (last $MONTHS_BACK months) have been properly closed.
Great job maintaining issue hygiene! 🎉

EOF
  fi

  # Add footer
  cat << EOF >> "$OUTPUT_FILE"

---

*This report was generated by \`scripts/audit_issue_hygiene.sh\`*
*Run with: \`./scripts/audit_issue_hygiene.sh\`*

EOF

  echo ""
  print_success "Report saved to: $OUTPUT_FILE"

  # Offer to open report
  if command -v open &> /dev/null && [[ "$OSTYPE" == "darwin"* ]]; then
    read -p "Open report in browser? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      # Convert markdown to HTML preview using gh
      gh markdown-preview "$OUTPUT_FILE" 2>/dev/null || cat "$OUTPUT_FILE"
    fi
  fi
}

# Main execution
main() {
  print_header "SkillForge Issue Hygiene Audit"

  check_prerequisites
  run_audit

  echo ""
  print_info "For automated monthly audits, see: .github/workflows/issue-hygiene-audit.yml"
}

# Run main function
main "$@"
