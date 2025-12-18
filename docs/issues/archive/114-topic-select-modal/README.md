# Issue #114: Topic Selection Modal

**Status:** ✅ **COMPLETE** (Frontend UI - Mock API)
**Assignee:** Arie
**Points:** 3 pts
**GitHub:** [#114](https://github.com/ArieGoldkin/SkillForge/issues/114)
**Sprint:** Sprint 4: Interactive Tutoring

---

## Overview

Implement the Topic Selection Modal and "Teach Me" entry points for starting tutoring sessions from completed analyses and artifact pages.

**User Story:** As a user who has completed a content analysis, I want to select a topic from the analysis to learn about through Socratic tutoring.

---

## Implementation Summary

### Entry Points

Two entry points were added for starting tutoring sessions:

1. **AnalysisCompleteCard** - "Teach Me" button between Preview and View Guide
2. **ArtifactHeader** - "Teach Me" button next to Download button

### User Flow

```
Analysis Complete → Teach Me → TopicSelectModal → Select Topic → /tutor/$sessionId
                                    ↓
Artifact Page → Teach Me → TopicSelectModal → Select Topic → /tutor/$sessionId
```

### Components Created

| Component | Location | Description |
|-----------|----------|-------------|
| `TeachMeButton` | `features/analysis/components/states/internal/` | Entry point button with modal trigger |
| `TopicSelectModal` | `features/tutor/components/TopicSelectModal/` | Modal with topic selection UI |
| `TopicList` | `TopicSelectModal/TopicList.tsx` | Radio group list of topics |
| `TopicContent` | `TopicSelectModal/TopicContent.tsx` | Loading/empty state handler |
| `useStartTutoring` | `features/tutor/hooks/` | Hook for fetching topics and creating sessions |

### Files Modified

| File | Change |
|------|--------|
| `ActionButtons.tsx` | Added TeachMeButton (middle position) |
| `ArtifactHeader.tsx` | Added TeachMeButton (next to Download) |
| `ArtifactPage.tsx` | Pass analysisId to header |
| `mock.service.ts` | Added `getTopics()` and updated `createSession()` |
| `api.ts` | Added `TutoringTopic` type |

### UI Components Added

- `label.tsx` - shadcn Label component
- `radio-group.tsx` - shadcn RadioGroup component

---

## Technical Details

### TopicSelectModal Props

```typescript
interface TopicSelectModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (topicId: string) => void
  topics: TutoringTopic[]
  isLoading?: boolean
  analysisTitle?: string
}
```

### useStartTutoring Hook

```typescript
interface UseStartTutoringOptions {
  analysisId: string
  onError?: (error: string) => void
}

function useStartTutoring(options: UseStartTutoringOptions) {
  return {
    topics: TutoringTopic[],
    isLoadingTopics: boolean,
    fetchTopics: () => Promise<void>,
    startTutoring: (topicId: string) => Promise<void>
  }
}
```

### Mock API

```typescript
mockTutoringAPI.getTopics(analysisId: string): Promise<TutoringTopic[]>
mockTutoringAPI.createSession(analysisId: string, topicId?: string): Promise<TutoringSession>
```

---

## Testing

### Unit Tests (13 total)

**TopicSelectModal.test.tsx** (8 tests):
- Renders modal with title when open
- Renders all topics
- Shows analysis title in description when provided
- Shows loading state when isLoading is true
- Shows empty state when no topics
- Enables Start Learning button when topic is selected
- Calls onSelect with topic id when Start Learning clicked
- Calls onClose when Cancel clicked

**TeachMeButton.test.tsx** (5 tests):
- Renders button with Teach Me text
- Renders with large size by default
- Renders with outline variant by default
- Opens modal when clicked
- Passes analysisTitle to modal

### Visual Testing

Verified with Playwright MCP:
- "Teach Me" button visible in AnalysisCompleteCard
- Modal opens with 4 mock topics
- Topic selection enables "Start Learning" button
- Navigation to `/tutor/$sessionId` works
- "Teach Me" button visible in ArtifactHeader
- Modal works from Artifact page

---

## Dependencies

### Requires (Backend - Not Yet Implemented)

| Issue | Title | Status |
|-------|-------|--------|
| #74 | Tutoring API Endpoints | Open |
| #79 | Tutoring Session Persistence | Open |
| #213 | Tutoring Workflow & Streaming | Open |

### Related Frontend Issues

| Issue | Title | Status |
|-------|-------|--------|
| #113 | TutorChat Component | Open |
| #115 | Session Resume Logic | Open |
| #116 | Exit Tutoring Functionality | Open |

---

## What's Still Needed

### Backend Integration (Issue #74)

Replace mock API calls with real endpoints:

```typescript
// Current (mock)
const topics = await mockTutoringAPI.getTopics(analysisId)
const session = await mockTutoringAPI.createSession(analysisId, topicId)

// Future (real API)
const topics = await api.get(`/api/v1/tutor/analyses/${analysisId}/topics`)
const session = await api.post(`/api/v1/tutor/sessions`, { analysis_id: analysisId, topic_id: topicId })
```

### TutorChat Page (Issue #113)

The `/tutor/$sessionId` route currently shows mock messages. Needs:
- Real-time SSE streaming
- Message input handling
- Session state management

### Session Resume (Issue #115)

When user returns to an existing session:
- Load conversation history
- Restore session state
- Continue from checkpoint

### Exit Session (Issue #116)

Allow user to:
- Mark session as completed
- Mark session as abandoned
- Return to analysis/artifact page

---

## Acceptance Criteria

- [x] TopicSelectModal component created
- [x] Topics displayed as selectable radio buttons
- [x] "Start Learning" button disabled until topic selected
- [x] Modal closes on Cancel or successful selection
- [x] Navigation to tutor session page works
- [x] "Teach Me" button in AnalysisCompleteCard
- [x] "Teach Me" button in ArtifactHeader
- [x] Unit tests with ≥80% coverage
- [x] Visual testing passed
- [ ] Real API integration (depends on #74)

---

## Design Reference

HTML prototype: `.superdesign/design_iterations/tutor_entry_point_1.html`

---

**Last Updated:** December 14, 2025
**PR:** [#TBD](https://github.com/ArieGoldkin/SkillForge/pull/new/issue/114-tutor-entry-point-ui)
