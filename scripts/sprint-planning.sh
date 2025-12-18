#!/bin/bash
# SkillForge Sprint Planning Assistant
# Automates sprint milestone creation and issue assignment

set -e

REPO="ArieGoldkin/SkillForge"
SPRINT_NAME="$1"
DUE_DATE="$2"

if [ -z "$SPRINT_NAME" ] || [ -z "$DUE_DATE" ]; then
  echo "Usage: $0 <sprint-name> <due-date>"
  echo ""
  echo "Example: $0 'Sprint 13' '2026-02-15'"
  echo ""
  echo "Creates a new sprint milestone and suggests issues to add"
  exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "     SkillForge Sprint Planning - $SPRINT_NAME"
echo "═══════════════════════════════════════════════════"
echo ""

# Create milestone
echo "📋 Creating milestone: $SPRINT_NAME (due: $DUE_DATE)"
MILESTONE_JSON=$(gh api -X POST repos/$REPO/milestones \
  -f title="$SPRINT_NAME" \
  -f state='open' \
  -f description="Sprint milestone created on $(date +%Y-%m-%d)" \
  -f due_on="${DUE_DATE}T23:59:59Z")

MILESTONE_NUMBER=$(echo "$MILESTONE_JSON" | jq -r '.number')
echo "✅ Created milestone #$MILESTONE_NUMBER"
echo ""

# Get project ID for Sprint Board
PROJECT_ID=$(gh project list --owner ArieGoldkin --format json | jq -r '.projects[] | select(.title == "SkillForge - Sprint Board") | .number')

if [ -z "$PROJECT_ID" ]; then
  echo "⚠️  Warning: Sprint Board project not found. Issues won't be added to project."
  PROJECT_ID=""
fi

# Find high-priority issues without milestones
echo "🎯 Suggested High-Priority Issues (no milestone assigned):"
echo ""
gh issue list --repo $REPO --search "no:milestone is:open sort:updated-desc" \
  --json number,title,labels,updatedAt \
  --jq '.[] |
    select(.labels | map(.name) | contains(["priority:high"]) or contains(["priority:critical"])) |
    "  #\(.number): \(.title)\n    Labels: \(.labels | map(.name) | join(", "))\n    Updated: \(.updatedAt[0:10])\n"' \
  | head -30

echo ""
echo "═══════════════════════════════════════════════════"
echo ""
read -p "Add issues to $SPRINT_NAME? (comma-separated numbers, or 'n' to skip): " ISSUE_NUMBERS

if [ "$ISSUE_NUMBERS" = "n" ] || [ -z "$ISSUE_NUMBERS" ]; then
  echo "Skipping issue assignment."
  echo ""
  echo "✅ Sprint milestone created!"
  echo "View at: https://github.com/$REPO/milestone/$MILESTONE_NUMBER"
  exit 0
fi

# Add issues to milestone and project
echo ""
echo "Adding issues to $SPRINT_NAME..."
IFS=',' read -ra ISSUES <<< "$ISSUE_NUMBERS"
for issue in "${ISSUES[@]}"; do
  issue=$(echo "$issue" | xargs)  # Trim whitespace

  # Add to milestone
  gh issue edit "$issue" --repo $REPO --milestone "$MILESTONE_NUMBER" 2>/dev/null && \
    echo "  ✅ #$issue added to milestone" || \
    echo "  ❌ Failed to add #$issue to milestone"

  # Add to Sprint Board project if available
  if [ -n "$PROJECT_ID" ]; then
    gh project item-add "$PROJECT_ID" --owner ArieGoldkin \
      --url "https://github.com/$REPO/issues/$issue" 2>/dev/null && \
      echo "     Added to Sprint Board" || true
  fi
done

echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ Sprint planning complete!"
echo ""
echo "📊 Summary:"
ISSUE_COUNT=$(gh api repos/$REPO/milestones/$MILESTONE_NUMBER | jq -r '.open_issues')
echo "  Milestone: $SPRINT_NAME (#$MILESTONE_NUMBER)"
echo "  Due Date: $DUE_DATE"
echo "  Issues: $ISSUE_COUNT"
echo ""
echo "View milestone: https://github.com/$REPO/milestone/$MILESTONE_NUMBER"
echo "═══════════════════════════════════════════════════"
