#!/bin/bash
# Setup script for GitHub Project board
# This script helps add issues to the project board once it's created
# Usage: ./scripts/setup-github-project.sh <project-number>

set -e

PROJECT_NUMBER=${1:-""}

if [ -z "$PROJECT_NUMBER" ]; then
    echo "Usage: ./scripts/setup-github-project.sh <project-number>"
    echo ""
    echo "First, create the project manually:"
    echo "1. Go to https://github.com/orgs/ArieGoldkin/projects/new"
    echo "2. Create project: 'SkillForge - Sprint Board'"
    echo "3. Note the project number"
    echo ""
    echo "Then run this script with the project number"
    exit 1
fi

OWNER="ArieGoldkin"
REPO="SkillForge"

echo "Adding issues to GitHub Project #${PROJECT_NUMBER}..."

# Sprint 1 Issues
ISSUES=(
    "1"   # Task 1.1.1 - Create FastAPI Project Structure [3 pts]
    "2"   # Task 1.1.2-1.1.3 - Environment Config & Logging [3 pts]
    "3"   # Task 1.2.1-1.2.5 - Database Schema & Migrations [8 pts]
    "4"   # Task 1.4.1-1.4.5 - Content Extraction (Jina AI) [5 pts]
    "5"   # Task 1.5.1-1.5.2 - Embedding Service [3 pts]
)

# Sprint 7 Issues
ISSUES+=(
    "7"   # Task 6.5-6.7, 7.5-7.7 - CI/CD Pipeline Setup [13 pts]
)

for issue_num in "${ISSUES[@]}"; do
    echo "Adding Issue #${issue_num} to project..."
    gh project item-add "${PROJECT_NUMBER}" --owner "${OWNER}" --url "https://github.com/${OWNER}/${REPO}/issues/${issue_num}" 2>&1 || echo "Failed to add Issue #${issue_num}"
done

echo ""
echo "✅ Added ${#ISSUES[@]} issues to project #${PROJECT_NUMBER}"
echo ""
echo "Next steps:"
echo "1. Configure project fields (Sprint, Story Points, Assignee, Status, Priority)"
echo "2. Set up automation rules (see docs/GITHUB_PROJECT_SETUP.md)"
echo "3. Organize issues into columns by status"
