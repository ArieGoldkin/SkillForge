# Documentation Organization Guide

**Last Updated:** November 21, 2025  
**Status:** ✅ **ORGANIZED**

---

## 📁 Current Documentation Structure

```
docs/
├── issues/                          # Issue-specific documentation
│   ├── README.md                    # Issues index
│   ├── 002-environment-config/
│   │   └── README.md               # Issue #2 complete doc
│   └── 003-database-schema/
│       └── README.md               # Issue #3 complete doc
│
├── reporter-accuracy-reference/     # Reference materials (archived)
│   ├── README.md
│   ├── REPORTER_ACCURACY_ANALYSIS.md
│   ├── REPORTER_ACCURACY_LEARNINGS.md
│   └── REPORTER_ACCURACY_QUICK_REF.md
│
├── ARCHITECTURE.md                  # System architecture diagrams
├── ARIE_FRONTEND_TASKS.md          # Frontend task breakdown
├── CURRENT_STATUS.md                # Current project status
├── GITHUB_PROJECT_SETUP.md         # GitHub setup guide
├── INTEGRATION_POINTS.md           # API contracts & coordination
├── PROJECT_SUMMARY.md              # Project overview
├── ROADMAP.md                      # Main project roadmap
├── ROADMAP_PARALLEL.md             # Parallel development plan
├── USER_STORIES.md                 # User stories with acceptance criteria
├── YONATAN_BACKEND_TASKS.md        # Backend task breakdown
│
└── issues/                          # Issue-specific documentation
    ├── README.md                    # Issues index
    ├── 002-environment-config/
    │   └── README.md                # Issue #2 complete doc
    └── 003-database-schema/
        └── README.md                # Issue #3 complete doc
```

---

## 📋 Documentation Standards

### Main Documentation (Root Level)

**Purpose:** Core project documentation that doesn't change frequently

- `ARCHITECTURE.md` - System architecture and diagrams
- `ROADMAP.md` - Project roadmap and phases
- `ROADMAP_PARALLEL.md` - Parallel development plan
- `USER_STORIES.md` - User stories with acceptance criteria
- `INTEGRATION_POINTS.md` - API contracts and coordination
- `CURRENT_STATUS.md` - Current project status (updated frequently)
- `YONATAN_BACKEND_TASKS.md` - Backend task breakdown
- `ARIE_FRONTEND_TASKS.md` - Frontend task breakdown

### Issue Documentation (`docs/issues/`)

**Purpose:** Documentation specific to GitHub issues

**Structure:**
```
docs/issues/
├── README.md              # Issues index with links
├── 002-issue-name/
│   └── README.md         # Consolidated issue doc
└── 003-issue-name/
    └── README.md         # Consolidated issue doc
```

**Each Issue Doc Should Include:**
1. Issue Overview (title, status, assignee, completion date)
2. Implementation Summary (tasks, commits, files)
3. Technical Details (architecture, patterns, dependencies)
4. Verification (tests, dev env, standards)
5. Related Documentation (links)

### Reference Documentation (`docs/reporter-accuracy-reference/`)

**Purpose:** Archived reference materials

- Original analysis documents
- Learnings from other projects
- Quick reference guides

---

## 🔗 GitHub Issues Integration

### Issue Documentation Workflow

1. **Create Issue** → GitHub issue created
2. **Start Work** → Create folder `docs/issues/XXX-issue-name/`
3. **Document Progress** → Update `README.md` in issue folder
4. **Link to Issue** → Add link in GitHub issue body
5. **Complete** → Mark issue complete, update index

### GitHub Issue Template

```markdown
## Description
[Full description]

## Tasks
- [ ] Task 1
- [ ] Task 2

## Documentation
- [Issue Doc](./docs/issues/002-issue-name/README.md)

## Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2

## Status
✅ COMPLETE / 🔄 IN PROGRESS / 📋 PLANNED
```

---

## 📊 Issues Index

See [docs/issues/README.md](./issues/README.md) for complete issues index.

---

## 🎯 Next Steps

1. ✅ Create organized structure (`docs/issues/`)
2. ✅ Consolidate Issue #2 and #3 docs
3. ⏭️ Archive old scattered docs (optional)
4. ⏭️ Update GitHub issues with doc links
5. ⏭️ Update main README with new structure

---

**Maintained By:** Yonatan & Arie
