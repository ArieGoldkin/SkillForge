#!/bin/bash
# SkillForge Milestone Progress Report
# Shows completion status for all active milestones

set -e

REPO="ArieGoldkin/SkillForge"

echo "═══════════════════════════════════════════════════"
echo "    SkillForge Milestone Progress - $(date +%Y-%m-%d)"
echo "═══════════════════════════════════════════════════"
echo ""

# Get milestone data and calculate progress
gh api repos/$REPO/milestones --paginate | jq -r '
  map(
    . + {
      completion: (
        if (.open_issues + .closed_issues) > 0
        then (.closed_issues * 100 / (.open_issues + .closed_issues))
        else 0
        end | floor
      ),
      progress_bar: (
        if (.open_issues + .closed_issues) > 0
        then (
          (.closed_issues * 20 / (.open_issues + .closed_issues) | floor) as $filled |
          (["█"] * $filled | join("")) + (["░"] * (20 - $filled) | join(""))
        )
        else "░░░░░░░░░░░░░░░░░░░░"
        end
      ),
      due_status: (
        if .due_on == null then "No due date"
        elif (.due_on | fromdateiso8601) < now then "⚠️  OVERDUE"
        elif (.due_on | fromdateiso8601) < (now + 7*24*3600) then "⏰ Due soon"
        else "✓ On track"
        end
      )
    }
  ) |
  sort_by(.due_on // "9999-99-99") |
  .[] |
  select(.state == "open") |
  "\n\(.title)\n[\(.progress_bar)] \(.completion)% (\(.closed_issues)/\(.open_issues + .closed_issues) issues)\nDue: \(.due_on[0:10] // "No date set") - \(.due_status)\n"
'

echo ""
echo "═══════════════════════════════════════════════════"

# Summary statistics
TOTAL_MILESTONES=$(gh api repos/$REPO/milestones | jq 'length')
OPEN_MILESTONES=$(gh api repos/$REPO/milestones | jq '[.[] | select(.state == "open")] | length')
TOTAL_ISSUES=$(gh api repos/$REPO/milestones | jq '[.[] | select(.state == "open") | .open_issues + .closed_issues] | add')
CLOSED_ISSUES=$(gh api repos/$REPO/milestones | jq '[.[] | select(.state == "open") | .closed_issues] | add')

if [ "$TOTAL_ISSUES" != "null" ] && [ "$TOTAL_ISSUES" != "0" ]; then
  OVERALL_COMPLETION=$((CLOSED_ISSUES * 100 / TOTAL_ISSUES))
  echo "📊 Overall Progress: $OVERALL_COMPLETION% ($CLOSED_ISSUES/$TOTAL_ISSUES issues)"
fi

echo "🎯 Active Milestones: $OPEN_MILESTONES"
echo "═══════════════════════════════════════════════════"
