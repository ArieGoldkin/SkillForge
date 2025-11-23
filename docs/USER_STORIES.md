# 📖 SkillForge - User Stories

**Version:** 1.0
**Last Updated:** November 21, 2025
**Project:** SkillForge - Research-to-Implementation Pipeline

---

## 📋 Table of Contents

1. [Epic 1: Content Analysis](#epic-1-content-analysis)
2. [Epic 2: AI Tutoring](#epic-2-ai-tutoring)
3. [Epic 3: Knowledge Library](#epic-3-knowledge-library)
4. [Epic 4: Multi-Source Support](#epic-4-multi-source-support)
5. [Story Point Reference](#story-point-reference)

---

## 🎯 Epic 1: Content Analysis

**Epic Goal:** Enable users to analyze technical content from URLs and receive actionable implementation guides.

---

### US-1.1: Submit URL for Analysis

**As a** developer learning new technologies
**I want to** paste a URL (article, video, or repo) into a simple input field
**So that** I can quickly start analyzing technical content without complex setup

**Acceptance Criteria:**
- [ ] User can paste any URL into an input field
- [ ] System validates URL format (shows error for invalid URLs)
- [ ] System detects content type (article, YouTube video, GitHub repo)
- [ ] User receives confirmation that analysis started (with analysis ID)
- [ ] Analysis begins within 2 seconds of submission

**Story Points:** 3
**Priority:** P0 (Must Have)
**Dependencies:** None
**Sprint:** Sprint 1

**Tasks:**
- [Frontend] Create URL input component with validation
- [Frontend] Add content type detection UI indicators
- [Backend] Create `/api/v1/analyze` POST endpoint
- [Backend] Implement URL validation logic
- [Backend] Create Analysis record in database

---

### US-1.2: View Real-Time Analysis Progress

**As a** user who submitted a URL
**I want to** see live progress updates as the system analyzes my content
**So that** I understand what's happening and know when analysis is complete

**Acceptance Criteria:**
- [ ] User sees progress bar or stage indicators
- [ ] Each stage shows: "Extracting content", "Analyzing with AI", "Generating artifact"
- [ ] Updates appear in real-time without page refresh (SSE)
- [ ] User can see which sub-agents are currently running
- [ ] Estimated time remaining is displayed
- [ ] User can cancel analysis in progress

**Story Points:** 5
**Priority:** P0 (Must Have)
**Dependencies:** US-1.1
**Sprint:** Sprint 2

**Tasks:**
- [Frontend] Build SSE client hook (useSSE)
- [Frontend] Create ProgressTracker component with stage visualization
- [Backend] Implement SSE endpoint `/api/v1/analyze/{id}/stream`
- [Backend] Emit progress events from LangGraph workflow
- [Backend] Add cancellation logic

---

### US-1.3: Download Implementation Artifact

**As a** user with a completed analysis
**I want to** download a markdown file with implementation guidance
**So that** I can paste it to my AI coding assistant (Claude Code, Cursor) and start implementing

**Acceptance Criteria:**
- [ ] User sees "Download" button when analysis completes
- [ ] Downloaded file is valid markdown (.md extension)
- [ ] Filename is descriptive (e.g., "react-19-streaming-guide.md")
- [ ] Markdown includes all sections: Summary, Findings, Implementation Plan, Claude Code Prompts
- [ ] Code blocks have proper syntax highlighting hints
- [ ] File size is reasonable (<500KB for typical analysis)

**Story Points:** 3
**Priority:** P0 (Must Have)
**Dependencies:** US-1.2
**Sprint:** Sprint 3

**Tasks:**
- [Frontend] Add download button with proper file handling
- [Frontend] Implement markdown preview modal
- [Backend] Create `/api/v1/artifacts/{id}/download` endpoint
- [Backend] Generate markdown from artifact template
- [Backend] Store artifacts in database

---

### US-1.4: Preview Artifact Before Downloading

**As a** user
**I want to** preview the generated markdown in the browser
**So that** I can quickly assess quality before downloading

**Acceptance Criteria:**
- [ ] User sees "Preview" button alongside "Download"
- [ ] Preview opens in modal or dedicated page
- [ ] Markdown renders with proper formatting
- [ ] Code blocks have syntax highlighting
- [ ] User can copy individual code snippets
- [ ] Preview is responsive on mobile devices

**Story Points:** 3
**Priority:** P1 (Should Have)
**Dependencies:** US-1.3
**Sprint:** Sprint 3

**Tasks:**
- [Frontend] Create MarkdownPreview component with react-markdown
- [Frontend] Add Prism.js for syntax highlighting
- [Frontend] Implement copy-to-clipboard for code blocks
- [Frontend] Style markdown (headings, lists, tables)

---

### US-1.5: Copy Claude Code Prompt Directly

**As a** user reviewing an artifact
**I want to** copy the "Claude Code Prompt" section with one click
**So that** I can paste it directly to my AI coding assistant without manual selection

**Acceptance Criteria:**
- [ ] "Claude Code Prompt" section has dedicated copy button
- [ ] Button copies full prompt text to clipboard
- [ ] User sees confirmation toast: "Copied to clipboard!"
- [ ] Prompt is formatted as plain text (no markdown syntax)
- [ ] Works on all major browsers (Chrome, Firefox, Safari)

**Story Points:** 2
**Priority:** P1 (Should Have)
**Dependencies:** US-1.4
**Sprint:** Sprint 3

**Tasks:**
- [Frontend] Add copy button to prompt sections
- [Frontend] Implement clipboard API with fallback
- [Frontend] Add toast notification on success
- [Backend] Format prompt section for easy copying

---

## 🎓 Epic 2: AI Tutoring

**Epic Goal:** Provide interactive Socratic learning for concepts discovered in analyzed content.

---

### US-2.1: Enter Tutoring Mode from Analysis

**As a** user who completed an analysis
**I want to** click "Teach Me" on my artifact
**So that** I can deeply understand the concepts through interactive dialogue

**Acceptance Criteria:**
- [ ] "Teach Me" button visible on completed analysis
- [ ] Button opens new tutoring session (separate view)
- [ ] Tutor greets user with context from analysis
- [ ] User sees available topics extracted from analysis
- [ ] Session starts within 3 seconds

**Story Points:** 3
**Priority:** P0 (Must Have)
**Dependencies:** US-1.3
**Sprint:** Sprint 4

**Tasks:**
- [Frontend] Add "Teach Me" button to artifact view
- [Frontend] Create TutorSession page component
- [Backend] Create `/api/v1/tutor/sessions` POST endpoint
- [Backend] Initialize tutor with analysis context
- [Backend] Extract available topics from agent findings

---

### US-2.2: Have Socratic Dialogue with AI Tutor

**As a** user in tutoring mode
**I want to** chat with an AI tutor that asks questions and adapts to my understanding
**So that** I learn concepts deeply rather than just reading explanations

**Acceptance Criteria:**
- [ ] User can type messages and send to tutor
- [ ] Tutor responds with questions, explanations, or examples
- [ ] Tutor adapts difficulty based on user responses
- [ ] Conversation flows naturally (feels like 1-on-1 teaching)
- [ ] Tutor uses examples from the original analyzed content
- [ ] Response time is <5 seconds per message

**Story Points:** 8
**Priority:** P0 (Must Have)
**Dependencies:** US-2.1
**Sprint:** Sprint 4

**Tasks:**
- [Frontend] Build chat interface (message list + input)
- [Frontend] Implement message sending/receiving
- [Backend] Create tutor LangGraph workflow
- [Backend] Implement Socratic response node
- [Backend] Implement understanding assessment node
- [Backend] Create `/api/v1/tutor/sessions/{id}/messages` POST endpoint

---

### US-2.3: Resume Tutoring Sessions

**As a** user who started a tutoring session
**I want to** resume from where I left off if I navigate away
**So that** I don't lose my learning progress

**Acceptance Criteria:**
- [ ] User sees "Resume Tutoring" if they have an active session
- [ ] Resuming loads full conversation history
- [ ] Conversation scrolls to last message
- [ ] User can continue chatting seamlessly
- [ ] Sessions persist across browser restarts

**Story Points:** 3
**Priority:** P1 (Should Have)
**Dependencies:** US-2.2
**Sprint:** Sprint 4

**Tasks:**
- [Frontend] Store session ID in localStorage
- [Frontend] Create "Resume Session" UI
- [Frontend] Implement conversation history loading
- [Backend] Store messages in tutoring_messages table
- [Backend] Create GET endpoint for session retrieval

---

### US-2.4: Exit Tutoring Session

**As a** user in an active tutoring session
**I want to** explicitly exit when I'm done learning
**So that** I can return to browsing my library or starting new analyses

**Acceptance Criteria:**
- [ ] User sees "Exit Tutoring" button in chat interface
- [ ] Clicking exit marks session as completed
- [ ] User is redirected to analysis view or home page
- [ ] Exited session shows "Completed" status
- [ ] User can view completed session history (read-only)

**Story Points:** 2
**Priority:** P1 (Should Have)
**Dependencies:** US-2.2
**Sprint:** Sprint 4

**Tasks:**
- [Frontend] Add "Exit" button to chat UI
- [Frontend] Implement session completion flow
- [Backend] Update session status to "completed"
- [Backend] Create read-only session viewer endpoint

---

## 📚 Epic 3: Knowledge Library

**Epic Goal:** Enable users to search, filter, and browse their past analyses.

---

### US-3.1: View All Past Analyses

**As a** returning user
**I want to** see a list of all my previous analyses
**So that** I can reference past learnings without re-analyzing

**Acceptance Criteria:**
- [ ] User sees library page with all analyses
- [ ] Each analysis shows: Title, URL, date, topics (tags)
- [ ] Analyses are sorted by most recent first
- [ ] Pagination loads 20 results at a time
- [ ] Empty state shows helpful message for new users
- [ ] Library loads in <1 second for 100+ analyses

**Story Points:** 5
**Priority:** P0 (Must Have)
**Dependencies:** US-1.3
**Sprint:** Sprint 5

**Tasks:**
- [Frontend] Create Library page component
- [Frontend] Build AnalysisCard component
- [Frontend] Implement pagination
- [Backend] Create `/api/v1/library` GET endpoint
- [Backend] Optimize database queries with indexes

---

### US-3.2: Search Analyses by Keyword

**As a** user with many analyses
**I want to** search by keyword (e.g., "React hooks", "LangGraph")
**So that** I can quickly find relevant past analyses

**Acceptance Criteria:**
- [ ] User sees search input at top of library
- [ ] Search triggers after 500ms of typing (debounced)
- [ ] Results show analyses matching title, content, or topics
- [ ] Search results highlight matching terms
- [ ] Search handles typos/synonyms (semantic search)
- [ ] "No results" message shows helpful suggestions

**Story Points:** 5
**Priority:** P0 (Must Have)
**Dependencies:** US-3.1
**Sprint:** Sprint 5

**Tasks:**
- [Frontend] Add search input with debounce
- [Frontend] Update query params on search
- [Backend] Implement full-text search (PostgreSQL tsvector)
- [Backend] Implement semantic search (PGVector)
- [Backend] Combine search results (70% keyword, 30% semantic)

---

### US-3.3: Filter by Content Type and Topics

**As a** user
**I want to** filter analyses by content type (article/video/repo) and topics
**So that** I can narrow down results to specific areas of interest

**Acceptance Criteria:**
- [ ] User sees filter dropdowns (content type, topics)
- [ ] Selecting filters immediately updates results
- [ ] Multiple topics can be selected (OR logic)
- [ ] Active filters are clearly visible
- [ ] User can clear all filters with one click
- [ ] Filter state persists in URL (shareable links)

**Story Points:** 5
**Priority:** P1 (Should Have)
**Dependencies:** US-3.1
**Sprint:** Sprint 5

**Tasks:**
- [Frontend] Create filter UI components (Radix Select)
- [Frontend] Implement multi-select for topics
- [Frontend] Update URL params on filter change
- [Backend] Add query parameter parsing for filters
- [Backend] Implement topic extraction during analysis

---

### US-3.4: Sort Analyses by Date or Popularity

**As a** user browsing my library
**I want to** sort by "Most Recent" or "Most Downloaded"
**So that** I can prioritize either latest findings or frequently referenced analyses

**Acceptance Criteria:**
- [ ] User sees sort dropdown (Recent, Popular)
- [ ] Selecting sort option immediately reorders results
- [ ] Sort state persists in URL
- [ ] Default sort is "Most Recent"
- [ ] "Popular" tracks download count

**Story Points:** 3
**Priority:** P2 (Nice to Have)
**Dependencies:** US-3.1
**Sprint:** Sprint 5

**Tasks:**
- [Frontend] Add sort selector UI
- [Frontend] Update query params on sort change
- [Backend] Track download_count in artifacts table
- [Backend] Implement sort logic in database query

---

## 🌐 Epic 4: Multi-Source Support

**Epic Goal:** Expand beyond articles to support YouTube videos and GitHub repositories.

---

### US-4.1: Analyze YouTube Tutorial Videos

**As a** developer learning from video tutorials
**I want to** paste a YouTube URL and get a transcript-based analysis
**So that** I can extract implementation guidance without watching the entire video

**Acceptance Criteria:**
- [ ] User can paste YouTube URLs (youtube.com or youtu.be)
- [ ] System extracts video transcript automatically
- [ ] Artifact includes video metadata (duration, title)
- [ ] Key findings reference specific timestamps (e.g., "[12:34] Speaker explains X")
- [ ] Analysis works for videos with auto-generated captions
- [ ] Graceful error for videos without transcripts

**Story Points:** 5
**Priority:** P1 (Should Have)
**Dependencies:** US-1.1
**Sprint:** Sprint 6

**Tasks:**
- [Backend] Create YouTube extractor service
- [Backend] Integrate youtube-transcript-api
- [Backend] Handle multiple caption languages
- [Backend] Customize artifact template for videos
- [Backend] Add timestamp extraction logic

---

### US-4.2: Analyze GitHub Repositories

**As a** developer evaluating open-source projects
**I want to** paste a GitHub repo URL and get an architecture analysis
**So that** I can understand the tech stack and integration patterns

**Acceptance Criteria:**
- [ ] User can paste GitHub repo URLs (github.com/org/repo)
- [ ] System extracts README and repo structure
- [ ] Artifact identifies tech stack (languages, frameworks)
- [ ] Analysis includes file structure overview
- [ ] Works only for public repositories
- [ ] Shows clear error for private repos

**Story Points:** 5
**Priority:** P1 (Should Have)
**Dependencies:** US-1.1
**Sprint:** Sprint 6

**Tasks:**
- [Backend] Create GitHub extractor service
- [Backend] Integrate PyGithub library
- [Backend] Extract README + repo metadata
- [Backend] Analyze file structure
- [Backend] Customize prompts for repo analysis

---

## 📏 Story Point Reference

**1 Point:** Simple task, <2 hours, minimal complexity
**Example:** Add a button, update text content

**2 Points:** Straightforward task, 2-4 hours, low complexity
**Example:** Implement copy-to-clipboard, add validation

**3 Points:** Moderate task, 4-8 hours, some complexity
**Example:** Create new component, simple API endpoint

**5 Points:** Complex task, 1-2 days, moderate complexity
**Example:** Implement search with backend, SSE client

**8 Points:** Very complex task, 2-3 days, high complexity
**Example:** LangGraph workflow, multi-agent orchestration

**13 Points:** Epic-level task, 3-5 days, very high complexity
**Example:** Full feature with frontend + backend + integration

---

## 🎯 User Story Priorities

**P0 (Must Have):** Core functionality required for MVP
**P1 (Should Have):** Important features that enhance UX
**P2 (Nice to Have):** Deferred to post-MVP

---

## 📊 Sprint Mapping

| Sprint | User Stories | Total Points |
|--------|--------------|--------------|
| Sprint 1 | US-1.1 | 3 |
| Sprint 2 | US-1.2 | 5 |
| Sprint 3 | US-1.3, US-1.4, US-1.5 | 8 |
| Sprint 4 | US-2.1, US-2.2, US-2.3, US-2.4 | 16 |
| Sprint 5 | US-3.1, US-3.2, US-3.3, US-3.4 | 18 |
| Sprint 6 | US-4.1, US-4.2 | 10 |

**Total Story Points:** 60

---

## 🔄 Story Status Tracking

Each user story should be tracked with:
- **Status:** Not Started | In Progress | In Review | Done
- **Assignee:** Arie, Yonatan, or Both
- **Sprint:** Sprint number
- **Blockers:** Any dependencies preventing completion

**Example:**
```
US-1.1: Submit URL for Analysis
Status: Done ✅
Assignee: Both (Frontend: Arie, Backend: Yonatan)
Sprint: Sprint 1
Blockers: None
```

---

**Document Maintained By:** Product Management
**Review Frequency:** Weekly during active development
