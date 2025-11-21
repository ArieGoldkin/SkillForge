# GitHub Project Setup for SkillForge

This document outlines how to set up and configure the GitHub Project board for managing SkillForge sprints and tasks, similar to the reporter-accuracy project structure.

## Project Creation

### Manual Steps (requires owner permissions)

1. **Create GitHub Project**
   - Go to: https://github.com/orgs/ArieGoldkin/projects/new
   - Or: Navigate to repository → Projects tab → New project
   - **Title:** `SkillForge - Sprint Board`
   - **Template:** Board (Kanban-style)
   - **Visibility:** Public (or Private based on repo settings)

### Project Structure

#### Columns (Status-based)

1. **Backlog** - Tasks not yet started
2. **To Do** - Ready to start (🎯 ready label)
3. **In Progress** - Currently being worked on (🚧 in-progress label)
4. **Review** - Ready for review (👀 review label)
5. **Done** - Completed (✅ done label)

#### Fields/Custom Fields

1. **Sprint** - Iteration field
   - Values: Sprint 1, Sprint 2, Sprint 3, Sprint 4, Sprint 5, Sprint 6, Sprint 7

2. **Story Points** - Number field
   - For tracking story points per issue

3. **Assignee** - User field
   - Assign to: Arie, Yonatan, or both

4. **Status** - Single select field
   - Options: Not Started, Ready, In Progress, Review, Done, Blocked

5. **Priority** - Single select field
   - Options: 🔥 Critical, ⚡ High, 🔄 Medium, 📋 Low

6. **Category** - Single select field
   - Options: 🔵 Backend, 🟣 Frontend, 🔧 Infrastructure, 🗄️ Database

#### Milestones

Create milestones for each sprint:

- **Sprint 1: Backend Foundation** (Weeks 1-2)
- **Sprint 2: Analysis Pipeline Foundation** (Weeks 3-4)
- **Sprint 3: Multi-Agent Complete** (Weeks 5-6)
- **Sprint 4: Tutoring System** (Weeks 7-8)
- **Sprint 5: Library & Search** (Weeks 9-10)
- **Sprint 6: Content Expansion** (Week 11)
- **Sprint 7: Testing & Deployment** (Weeks 12-13)

## Adding Issues to Project

Once the project is created, add all existing issues:

### Sprint 1 Issues
- Issue #1: Task 1.1.1 - Create FastAPI Project Structure [3 pts]
- Issue #2: Task 1.1.2-1.1.3 - Environment Config & Logging [3 pts]
- Issue #3: Task 1.2.1-1.2.5 - Database Schema & Migrations [8 pts]
- Issue #4: Task 1.4.1-1.4.5 - Content Extraction (Jina AI) [5 pts]
- Issue #5: Task 1.5.1-1.5.2 - Embedding Service [3 pts]

### Sprint 7 Issues
- Issue #7: Task 6.5-6.7, 7.5-7.7 - CI/CD Pipeline Setup [13 pts]
- Issue #9: Task 7.8 - GitHub Project Setup [3 pts]

## Project Views

Create filtered views for better organization:

1. **By Sprint**
   - Filter: Sprint = Sprint 1
   - Shows all Sprint 1 tasks

2. **By Team Member**
   - Filter: Assignee = Yonatan
   - Shows all backend tasks

3. **By Status**
   - Filter: Status = In Progress
   - Shows active work

4. **By Priority**
   - Filter: Priority = ⚡ High or 🔥 Critical
   - Shows urgent items

## Automation (Optional)

Set up automation rules:

- **When issue is labeled `🎯 ready`** → Move to "To Do" column
- **When issue is labeled `🚧 in-progress`** → Move to "In Progress" column
- **When issue is labeled `👀 review`** → Move to "Review" column
- **When issue is labeled `✅ done`** → Move to "Done" column
- **When PR is merged** → Auto-label `✅ done` and move to "Done"

## Usage

1. **Sprint Planning**
   - Assign issues to appropriate sprint milestone
   - Set story points and assignees
   - Move issues to "To Do" when ready

2. **Daily Standup**
   - Update issue status
   - Move cards between columns
   - Identify blockers

3. **Sprint Review**
   - Review "Done" column
   - Calculate velocity (story points completed)
   - Plan next sprint

## Integration with Issues

Each issue in the project should:
- Be linked to a milestone (sprint)
- Have appropriate labels (category, priority, sprint-X)
- Have story points documented
- Have assignee set
- Track status in project board
