#!/bin/bash
# SkillForge Daily Standup Report
# Generates daily team status summary

set -e

REPO="ArieGoldkin/SkillForge"

echo "═══════════════════════════════════════════════════"
echo "      SkillForge Daily Standup - $(date +%Y-%m-%d)"
echo "═══════════════════════════════════════════════════"
echo ""

# Sprint Progress
echo "📊 Sprint Progress:"
gh api repos/$REPO/milestones | jq -r '
  .[] |
  select(.state == "open") |
  . + {
    completion: (
      if (.open_issues + .closed_issues) > 0
      then (.closed_issues * 100 / (.open_issues + .closed_issues) | floor)
      else 0
      end
    )
  } |
  "  \(.title): \(.completion)% complete (\(.closed_issues)/\(.open_issues + .closed_issues) issues)"
' | head -5

echo ""
echo "🎯 In Progress (Updated Last 24h):"
gh issue list --repo $REPO --label "status:in-progress" \
  --json number,title,assignees,updatedAt \
  --jq '.[] | select(.updatedAt > (now - 86400 | todate)) | "  #\(.number): \(.title) (@\(.assignees[0].login // "unassigned"))"' \
  | head -10 || echo "  No issues in progress"

echo ""
echo "✅ Completed Yesterday:"
YESTERDAY=$(date -d '1 day ago' +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
gh issue list --repo $REPO --state closed --search "closed:>=$YESTERDAY" \
  --json number,title --jq '.[] | "  #\(.number): \(.title)"' \
  | head -5 || echo "  No issues completed"

echo ""
echo "🚨 Blocked Issues:"
gh issue list --repo $REPO --label "status:blocked" \
  --json number,title,assignees \
  --jq '.[] | "  #\(.number): \(.title) (@\(.assignees[0].login // "unassigned"))"' \
  || echo "  No blocked issues"

echo ""
echo "🆕 New Issues (Last 24h):"
gh issue list --repo $REPO --search "created:>=$YESTERDAY" \
  --json number,title,labels \
  --jq '.[] | "  #\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"' \
  | head -5 || echo "  No new issues"

echo ""
echo "═══════════════════════════════════════════════════"
echo "💡 Tip: Run 'gh issue list --label status:in-progress' for details"
echo "═══════════════════════════════════════════════════"
