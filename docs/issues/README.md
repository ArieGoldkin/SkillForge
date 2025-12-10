# Issues Documentation Index

**Last Updated:** December 10, 2025
**Status:** ✅ **ORGANIZED**
**Current Sprint:** Sprint 8 - Embeddings & Search

---

## 🗺️ Sprint Progression

```
Sprint 8 (Current) → 9 (MCP Consumer) → 10 (Context Engineering) → 11 (Features) → 12 (MCP Server) → Testing
```

---

## 📋 Issues Overview

This directory contains documentation for each GitHub issue, organized by issue number.

### Structure

```
docs/issues/
├── README.md                              # This file (issues index)
├── 001-fastapi-structure/
│   ├── README.md                         # Issue #1 complete doc
│   └── ISSUE_1_VALIDATION_COMPLETE.md
├── 002-environment-config/
│   ├── README.md                         # Issue #2 complete doc
│   └── ISSUE_2_VALIDATION_COMPLETE.md
├── 003-database-schema/
│   ├── README.md                         # Issue #3 complete doc
│   └── ISSUE_3_VALIDATION_COMPLETE.md
├── 004-content-extraction-jina/
│   ├── README.md                         # Issue #4 complete doc
│   ├── ISSUE_4_VERIFICATION.md
│   └── TEST_RESULTS.md
├── 005-embedding-service/
│   └── README.md                         # Issue #5 complete doc
├── 030-frontend-code-quality/
│   ├── README.md                         # Issue #30 complete doc
│   └── ISSUE_30_VALIDATION_COMPLETE.md
├── 032-react-components/
│   ├── README.md                         # Issue #32 Phase 1-3 complete
│   └── ISSUE_32_VALIDATION_COMPLETE.md
├── 034-app-router-integration/
│   └── README.md                         # Issue #34 complete doc
├── 039-langgraph-workflow/
│   ├── README.md                         # Issue #39 complete doc
│   └── ISSUE_39_VERIFICATION.md
├── 040-sse-endpoint/
│   ├── README.md                         # Issue #40 complete doc
│   └── SSE_SCHEMA.md
├── 041-supervisor-pattern/
│   └── README.md                         # Issue #41 complete doc
├── 042-first-3-agents/
│   └── README.md                         # Issue #42 complete doc
├── 043-sse-client-hook/
│   └── ISSUE_43_VALIDATION_COMPLETE.md   # Issue #43 complete doc
├── 044-progress-tracker/
│   └── ISSUE_44_VALIDATION_COMPLETE.md   # Issue #44 complete doc
├── 045-analysis-view-page/
│   └── ISSUE_45_VALIDATION_COMPLETE.md   # Issue #45 complete doc
├── 060-markdown-dependencies/
│   └── README.md                         # Issue #60 complete doc
├── 061-artifact-page/
│   └── README.md                         # Issue #61 complete doc
├── 063-preview-modal/
│   └── README.md                         # Issue #63 complete doc
├── 070-remaining-5-agents/
│   └── README.md                         # Issue #70 complete doc
├── 071-aggregator-node/
│   └── README.md                         # Issue #71 complete doc
├── 072-artifact-generation/
│   └── README.md                         # Issue #72 complete doc
├── 090-embedding-token-fix/
│   └── README.md                         # Issue #90 open doc
├── 091-workflow-status-fix/
│   └── README.md                         # Issue #91 open doc
├── 092-extraction-error-handling/
│   └── README.md                         # Issue #92 open doc
├── 164-sse-progress-stuck/
│   └── README.md                         # Issue #164 complete doc
└── 165-skipped-agents-pending/
    └── README.md                         # Issue #165 complete doc
```

---

## 📊 Sprint 1 & 2 Issues Status

### ✅ Completed Issues (15 total)

| Issue | Title | Status | Assignee | Docs | GitHub |
|-------|-------|--------|----------|------|--------|
| [#1](https://github.com/ArieGoldkin/SkillForge/issues/1) | FastAPI Project Structure | ✅ Complete (Closed) | Yonatan | [📄 Docs](./001-fastapi-structure/README.md) | [#1](https://github.com/ArieGoldkin/SkillForge/issues/1) |
| [#2](https://github.com/ArieGoldkin/SkillForge/issues/2) | Environment Config & Logging | ✅ Complete | Yonatan | [📄 Docs](./002-environment-config/README.md) | [#2](https://github.com/ArieGoldkin/SkillForge/issues/2) |
| [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) | Database Schema & Migrations | ✅ Complete | Yonatan | [📄 Docs](./003-database-schema/README.md) | [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) |
| [#4](https://github.com/ArieGoldkin/SkillForge/issues/4) | Content Extraction (Jina AI) | ✅ Complete | Yonatan | [📄 Docs](./004-content-extraction-jina/README.md) | [#4](https://github.com/ArieGoldkin/SkillForge/issues/4) |
| [#5](https://github.com/ArieGoldkin/SkillForge/issues/5) | Embedding Service Implementation | ✅ Complete | Yonatan | [📄 Docs](./005-embedding-service/README.md) | [#5](https://github.com/ArieGoldkin/SkillForge/issues/5) |
| [#30](https://github.com/ArieGoldkin/SkillForge/issues/30) | Frontend Code Quality & Design Prototypes | ✅ Complete (Closed) | Arie | [📄 Docs](./030-frontend-code-quality/README.md) | [#30](https://github.com/ArieGoldkin/SkillForge/issues/30) |
| [#32](https://github.com/ArieGoldkin/SkillForge/issues/32) | Convert HTML Prototypes to React | 🟡 **Phase 1-3 Complete (75%)** | Arie | [📄 Docs](./032-react-components/README.md) | [#32](https://github.com/ArieGoldkin/SkillForge/issues/32) |
| [#34](https://github.com/ArieGoldkin/SkillForge/issues/34) | Integrate App.tsx with Router Layout | ✅ Complete | Arie | [📄 Docs](./034-app-router-integration/README.md) | [#34](https://github.com/ArieGoldkin/SkillForge/issues/34) |
| [#39](https://github.com/ArieGoldkin/SkillForge/issues/39) | Create Basic LangGraph Workflow | ✅ Complete | Yonatan | [📄 Docs](./039-langgraph-workflow/README.md) | [#39](https://github.com/ArieGoldkin/SkillForge/issues/39) |
| [#40](https://github.com/ArieGoldkin/SkillForge/issues/40) | SSE Endpoint for Real-Time Progress | ✅ Complete | Yonatan | [📄 Docs](./040-sse-endpoint/README.md) | [#40](https://github.com/ArieGoldkin/SkillForge/issues/40) |
| [#41](https://github.com/ArieGoldkin/SkillForge/issues/41) | Implement Supervisor Pattern | ✅ Complete (PR #57) | Yonatan | [📄 Docs](./041-supervisor-pattern/README.md) | [#41](https://github.com/ArieGoldkin/SkillForge/issues/41) |
| [#42](https://github.com/ArieGoldkin/SkillForge/issues/42) | Implement First 3 Core Sub-Agents | ✅ Complete (PR #58) | Yonatan | [📄 Docs](./042-first-3-agents/README.md) | [#42](https://github.com/ArieGoldkin/SkillForge/issues/42) |
| [#43](https://github.com/ArieGoldkin/SkillForge/issues/43) | Create SSE Client Hook [5 pts] | ✅ Complete | Arie | [📄 Docs](./043-sse-client-hook/ISSUE_43_VALIDATION_COMPLETE.md) | [#43](https://github.com/ArieGoldkin/SkillForge/issues/43) |
| [#44](https://github.com/ArieGoldkin/SkillForge/issues/44) | Build ProgressTracker Component [5 pts] | ✅ Complete | Arie | [📄 Docs](./044-progress-tracker/ISSUE_44_VALIDATION_COMPLETE.md) | [#44](https://github.com/ArieGoldkin/SkillForge/issues/44) |
| [#45](https://github.com/ArieGoldkin/SkillForge/issues/45) | Build Analysis View Page [3 pts] | ✅ Complete | Arie | [📄 Docs](./045-analysis-view-page/ISSUE_45_VALIDATION_COMPLETE.md) | [#45](https://github.com/ArieGoldkin/SkillForge/issues/45) |

### ✅ Recently Completed

| Issue | Title | Points | Status | Assignee | Docs | GitHub |
|-------|-------|--------|--------|----------|------|--------|
| [#68](https://github.com/ArieGoldkin/SkillForge/issues/68) | Docker Compose Configuration | 3 | ✅ Complete | Yonatan | [📄 Docs](./068-docker-compose/README.md) | [#68](https://github.com/ArieGoldkin/SkillForge/issues/68) |
| [#71](https://github.com/ArieGoldkin/SkillForge/issues/71) | Aggregator Node | 5 | ✅ Complete | Yonatan | [📄 Docs](./071-aggregator-node/README.md) | [#71](https://github.com/ArieGoldkin/SkillForge/issues/71) |
| [#72](https://github.com/ArieGoldkin/SkillForge/issues/72) | Artifact Generation | 8 | ✅ Complete | Yonatan | [📄 Docs](./072-artifact-generation/README.md) | [#72](https://github.com/ArieGoldkin/SkillForge/issues/72) |
| [#143](https://github.com/ArieGoldkin/SkillForge/issues/143) | Fix Agent Type Mismatch and SSE Workflow Completion | 3 | ✅ Complete | Yonatan | [📄 Docs](./143-sse-workflow-completion-fix/README.md) | [#143](https://github.com/ArieGoldkin/SkillForge/issues/143) |
| [#164](https://github.com/ArieGoldkin/SkillForge/issues/164) | UI Progress stuck at 55% - handle 'workflow' stage | 3 | ✅ Complete | Arie | [📄 Docs](./164-sse-progress-stuck/README.md) | [#164](https://github.com/ArieGoldkin/SkillForge/issues/164) |
| [#165](https://github.com/ArieGoldkin/SkillForge/issues/165) | Skipped agents show 'pending' instead of 'skipped' | 2 | ✅ Complete | Arie | [📄 Docs](./165-skipped-agents-pending/README.md) | [#165](https://github.com/ArieGoldkin/SkillForge/issues/165) |
| [#113](https://github.com/ArieGoldkin/SkillForge/issues/113) | TutorChat Component | 5 | ✅ Complete | Arie | — | [#113](https://github.com/ArieGoldkin/SkillForge/issues/113) |
| [#117](https://github.com/ArieGoldkin/SkillForge/issues/117) | Create Library Page | 5 | ✅ Complete | Arie | — | [#117](https://github.com/ArieGoldkin/SkillForge/issues/117) |
| [#118](https://github.com/ArieGoldkin/SkillForge/issues/118) | Search with Debounce | 3 | ✅ Complete | Arie | — | [#118](https://github.com/ArieGoldkin/SkillForge/issues/118) |
| [#119](https://github.com/ArieGoldkin/SkillForge/issues/119) | Build Filter UI | 3 | ✅ Complete | Arie | — | [#119](https://github.com/ArieGoldkin/SkillForge/issues/119) |

### 🔄 In Progress / Ready (7 total - 20 pts)

#### Backend (Yonatan)

| Issue | Title | Points | Status | Assignee | Docs | GitHub |
|-------|-------|--------|--------|----------|------|--------|
| [#90](https://github.com/ArieGoldkin/SkillForge/issues/90) | Fix Embedding Token Limit Violation | 5 | ✅ Complete | Yonatan | [📄 Docs](./090-embedding-token-fix/README.md) | [#90](https://github.com/ArieGoldkin/SkillForge/issues/90) |
| [#91](https://github.com/ArieGoldkin/SkillForge/issues/91) | Fix Workflow Status Not Updated to Complete | 3 | ✅ Complete | Yonatan | [📄 Docs](./091-workflow-status-fix/README.md) | [#91](https://github.com/ArieGoldkin/SkillForge/issues/91) |
| [#92](https://github.com/ArieGoldkin/SkillForge/issues/92) | Improve Content Extraction Error Handling | 2 | ✅ Complete | Yonatan | [📄 Docs](./092-extraction-error-handling/README.md) | [#92](https://github.com/ArieGoldkin/SkillForge/issues/92) |
| [#93](https://github.com/ArieGoldkin/SkillForge/issues/93) | Implement Similarity Search Using Embeddings | 8 | 🔄 Open | TBD | [📄 Docs](./093-embeddings-similarity-search/README.md) | TBD |

#### Frontend (Arie)

| Issue | Title | Status | Assignee | Docs | GitHub |
|-------|-------|--------|----------|------|--------|
| [#31](https://github.com/ArieGoldkin/SkillForge/issues/31) | Setup Testing Infrastructure | 🔄 Ready | Arie | TBD | [#31](https://github.com/ArieGoldkin/SkillForge/issues/31) |
| [#33](https://github.com/ArieGoldkin/SkillForge/issues/33) | Initialize Husky Pre-commit Hooks | 🔄 Ready | Arie | TBD | [#33](https://github.com/ArieGoldkin/SkillForge/issues/33) |
| [#35](https://github.com/ArieGoldkin/SkillForge/issues/35) | Add Error Boundaries and 404 Page | 🔄 Ready | Arie | TBD | [#35](https://github.com/ArieGoldkin/SkillForge/issues/35) |

### 📈 Sprint Progress

**Sprint 1:**
- **Total Story Points:** 45 pts
- **Completed:** 46 pts (102%) - *includes 6pts from Issue #32 Phase 1-3*
- **Remaining:** 0 pts (0%)
- **Yonatan Progress:** 29/27 pts (107%) ✅
- **Arie Progress:** 17/23 pts (74%) - *6pts from Issue #32*

**Sprint 2:**
- **Completed:** 35 pts (Issues #39 ✅, #40 ✅, #41 ✅, #42 ✅, #43 ✅, #44 ✅, #45 ✅)
- **Yonatan Progress:** 22/24 pts (92%)
- **Arie Progress:** 13/13 pts (100%) ✅

---

## 🚀 Sprint 3: Artifact Viewer + Integration (16 pts)

### Frontend Issues (Arie)

| Issue | Title | Points | Status | Assignee | Docs | GitHub |
|-------|-------|--------|--------|----------|------|--------|
| [#60](https://github.com/ArieGoldkin/SkillForge/issues/60) | Task 3.1 - Install Markdown Dependencies | 1 | ✅ Complete | Arie | [📄 Docs](./060-markdown-dependencies/README.md) | [#60](https://github.com/ArieGoldkin/SkillForge/issues/60) |
| [#61](https://github.com/ArieGoldkin/SkillForge/issues/61) | Task 3.2 - Artifact Page with Markdown Preview | 5 | ✅ Complete | Arie | [📄 Docs](./061-artifact-page/README.md) | [#61](https://github.com/ArieGoldkin/SkillForge/issues/61) |
| [#62](https://github.com/ArieGoldkin/SkillForge/issues/62) | Task 3.3 - Artifact Download Handler | 2 | ✅ Included in #61 | Arie | — | [#62](https://github.com/ArieGoldkin/SkillForge/issues/62) |
| [#63](https://github.com/ArieGoldkin/SkillForge/issues/63) | Task 3.4 - Preview Modal | 3 | ✅ Complete | Arie | [📄 Docs](./063-preview-modal/README.md) | [#63](https://github.com/ArieGoldkin/SkillForge/issues/63) |
| [#64](https://github.com/ArieGoldkin/SkillForge/issues/64) | Task 3.5 - Copy-to-Clipboard | 2 | ✅ Included in #61 | Arie | — | [#64](https://github.com/ArieGoldkin/SkillForge/issues/64) |
| [#65](https://github.com/ArieGoldkin/SkillForge/issues/65) | Task 3.6 - Frontend-Backend Integration | 3 | ⏳ Blocked | Arie | — | [#65](https://github.com/ArieGoldkin/SkillForge/issues/65) |

---

## 🎓 Sprint 4: Interactive Tutoring (13 pts)

### Frontend Issues (Arie)

| Issue | Title | Points | Status | Assignee | GitHub |
|-------|-------|--------|--------|----------|--------|
| [#113](https://github.com/ArieGoldkin/SkillForge/issues/113) | Task 4.1 - Create TutorChat Component | 5 | ✅ Complete | Arie | [#113](https://github.com/ArieGoldkin/SkillForge/issues/113) |
| [#114](https://github.com/ArieGoldkin/SkillForge/issues/114) | Task 4.2 - Create Topic Selection Modal | 3 | 🔄 Open | Arie | [#114](https://github.com/ArieGoldkin/SkillForge/issues/114) |
| [#115](https://github.com/ArieGoldkin/SkillForge/issues/115) | Task 4.3 - Implement Session Resume Logic | 3 | 🔄 Open | Arie | [#115](https://github.com/ArieGoldkin/SkillForge/issues/115) |
| [#116](https://github.com/ArieGoldkin/SkillForge/issues/116) | Task 4.4 - Add Exit Tutoring Functionality | 2 | 🔄 Open | Arie | [#116](https://github.com/ArieGoldkin/SkillForge/issues/116) |

**Sprint 4 Progress:** 5/13 pts (38%) - TutorChat component implemented in `features/tutor/`

---

## 📚 Sprint 5: Library & Search (13 pts)

### Frontend Issues (Arie)

| Issue | Title | Points | Status | Assignee | GitHub |
|-------|-------|--------|--------|----------|--------|
| [#117](https://github.com/ArieGoldkin/SkillForge/issues/117) | Task 5.1 - Create Library Page | 5 | ✅ Complete | Arie | [#117](https://github.com/ArieGoldkin/SkillForge/issues/117) |
| [#118](https://github.com/ArieGoldkin/SkillForge/issues/118) | Task 5.2 - Implement Search with Debounce | 3 | ✅ Complete | Arie | [#118](https://github.com/ArieGoldkin/SkillForge/issues/118) |
| [#119](https://github.com/ArieGoldkin/SkillForge/issues/119) | Task 5.3 - Build Filter UI | 3 | ✅ Complete | Arie | [#119](https://github.com/ArieGoldkin/SkillForge/issues/119) |
| [#120](https://github.com/ArieGoldkin/SkillForge/issues/120) | Task 5.4 - Add Sort Selector | 2 | 🔄 Open | Arie | [#120](https://github.com/ArieGoldkin/SkillForge/issues/120) |

**Sprint 5 Progress:** 11/13 pts (85%) - Library page with search and filters implemented in `features/library/`

---

## 🌐 Sprint 6: Content Expansion (8 pts)

### Frontend Issues (Arie)

| Issue | Title | Points | Status | Assignee | GitHub |
|-------|-------|--------|--------|----------|--------|
| [#121](https://github.com/ArieGoldkin/SkillForge/issues/121) | Task 6.1 - Add Content Type Indicators | 3 | 🔄 Open | Arie | [#121](https://github.com/ArieGoldkin/SkillForge/issues/121) |
| [#122](https://github.com/ArieGoldkin/SkillForge/issues/122) | Task 6.2 - Update Artifact Template for Videos | 3 | 🔄 Open | Arie | [#122](https://github.com/ArieGoldkin/SkillForge/issues/122) |
| [#123](https://github.com/ArieGoldkin/SkillForge/issues/123) | Task 6.3 - Update Artifact Template for Repos | 2 | 🔄 Open | Arie | [#123](https://github.com/ArieGoldkin/SkillForge/issues/123) |

---

## 🚀 Sprint 7: Testing & Deployment (21 pts)

### Frontend Issues (Arie)

| Issue | Title | Points | Status | Assignee | GitHub |
|-------|-------|--------|--------|----------|--------|
| [#125](https://github.com/ArieGoldkin/SkillForge/issues/125) | Task 7.1 - Write E2E Tests with Playwright | 8 | 🔄 Open | Arie | [#125](https://github.com/ArieGoldkin/SkillForge/issues/125) |
| [#126](https://github.com/ArieGoldkin/SkillForge/issues/126) | Task 7.2 - Performance Optimization | 5 | 🔄 Open | Arie | [#126](https://github.com/ArieGoldkin/SkillForge/issues/126) |
| [#127](https://github.com/ArieGoldkin/SkillForge/issues/127) | Task 7.3 - Deploy to Vercel | 3 | 🔄 Open | Arie | [#127](https://github.com/ArieGoldkin/SkillForge/issues/127) |
| [#124](https://github.com/ArieGoldkin/SkillForge/issues/124) | Task 7.4 - UI Polish | 5 | 🔄 Open | Arie | [#124](https://github.com/ArieGoldkin/SkillForge/issues/124) |

---

## 📝 Sprint 1: Missing Foundation Tasks (13 pts)

### Frontend Issues (Arie) - Created for Tracking

| Issue | Title | Points | Status | Assignee | GitHub |
|-------|-------|--------|--------|----------|--------|
| [#128](https://github.com/ArieGoldkin/SkillForge/issues/128) | Task 1.3.1 - Initialize Vite + React 19 Project | 3 | 🔄 Open | Arie | [#128](https://github.com/ArieGoldkin/SkillForge/issues/128) |
| [#129](https://github.com/ArieGoldkin/SkillForge/issues/129) | Task 1.3.2 - Setup Tailwind CSS + Radix UI | 2 | 🔄 Open | Arie | [#129](https://github.com/ArieGoldkin/SkillForge/issues/129) |
| [#130](https://github.com/ArieGoldkin/SkillForge/issues/130) | Task 1.3.3 - Configure React Router | 2 | 🔄 Open | Arie | [#130](https://github.com/ArieGoldkin/SkillForge/issues/130) |
| [#131](https://github.com/ArieGoldkin/SkillForge/issues/131) | Task 1.3.4 - Setup State Management | 3 | 🔄 Open | Arie | [#131](https://github.com/ArieGoldkin/SkillForge/issues/131) |
| [#132](https://github.com/ArieGoldkin/SkillForge/issues/132) | Task 1.3.5 - Create Page Shells & Basic Components | 3 | 🔄 Open | Arie | [#132](https://github.com/ArieGoldkin/SkillForge/issues/132) |

**Note:** These tasks appear to be completed (setup exists in codebase), but issues were created for tracking purposes.

### Backend Blockers

| Endpoint | Description | Blocks | Owner |
|----------|-------------|--------|-------|
| `POST /api/v1/analyze` | Start new analysis | All Sprint 3 | Yonatan (Task 1.4.3) |
| `GET /api/v1/artifacts/{id}` | Fetch artifact content | #61, #63 | Yonatan |
| `GET /api/v1/artifacts/{id}/download` | Download artifact | #62 | Yonatan |

### Already Implemented (Ready for Integration)

| Component | Description | Status |
|-----------|-------------|--------|
| SSE Endpoint | `GET /api/v1/analyze/{id}/stream` | ✅ Ready |
| LangGraph Workflow | Multi-agent analysis | ✅ Ready |
| Supervisor Pattern | Agent coordination | ✅ Ready |
| Frontend SSE Hook | `useSSE` hook | ✅ Ready |
| ProgressTracker | Progress UI component | ✅ Ready |

---

## 📖 Documentation Standards

Each issue doc (`XXX-issue-name/README.md`) should include:

1. **Issue Overview** - Title, status, assignee, completion date
2. **Implementation Summary** - Tasks completed, commits made, files changed
3. **Technical Details** - Architecture decisions, patterns used, dependencies
4. **Verification** - Test coverage, dev environment verification, standards compliance
5. **Related Documentation** - Links to task docs, related issues

---

## 🔗 Quick Links

- [Backend Tasks](../YONATAN_BACKEND_TASKS.md)
- [Frontend Tasks](../ARIE_FRONTEND_TASKS.md)
- [Current Status](../CURRENT_STATUS.md)
- [GitHub Issues](https://github.com/ArieGoldkin/SkillForge/issues)

---

**Maintained By:** Yonatan & Arie
