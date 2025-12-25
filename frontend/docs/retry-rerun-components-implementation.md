# Retry and Rerun Functionality - Frontend Implementation

**Created:** December 25, 2025
**Status:** Complete - All components, hooks, and API methods implemented
**Quality:** All TypeScript, ESLint, and Biome checks passing

## Overview

Implemented complete retry/rerun functionality for failed and completed analyses with TypeScript strict mode, proper state management, and comprehensive error handling.

## Components Created

### 1. Action Components

#### `RetryButton.tsx`
**Location:** `/frontend/src/features/analysis/components/actions/RetryButton.tsx`

**Purpose:** Retry failed analyses with max retry limit (3)

**Features:**
- Retry counter showing remaining attempts
- Disabled state when max retries reached
- Loading state with animated icon during retry
- Error display for failed retry attempts
- Max retries warning alert

**Props:**
```typescript
interface RetryButtonProps {
  analysisId: string
  retryCount: number
  maxRetries?: number  // default: 3
  onRetry: () => void
  isRetrying: boolean
  retryError?: string
}
```

#### `RerunButton.tsx`
**Location:** `/frontend/src/features/analysis/components/actions/RerunButton.tsx`

**Purpose:** Rerun completed analyses with latest AI models/prompts

**Features:**
- Tooltip explaining rerun behavior
- Rerun count badge
- Loading state with animated icon
- Error display for failed rerun attempts
- Informative tooltip with feature list

**Props:**
```typescript
interface RerunButtonProps {
  analysisId: string
  rerunCount?: number
  onRerun: () => void
  isRerunning: boolean
  rerunError?: string
}
```

### 2. Card Components

#### `AnalysisActionsCard.tsx`
**Location:** `/frontend/src/features/analysis/components/cards/AnalysisActionsCard.tsx`

**Purpose:** Context-aware action card that displays appropriate button based on analysis status

**Features:**
- Automatic retry/rerun selection based on status
- Error details display for failed analyses
- Status badge with color coding
- Contextual descriptions
- Null render for non-actionable statuses

**Props:**
```typescript
interface AnalysisActionsCardProps {
  analysisId: string
  status: AnalysisStatus
  retryCount?: number
  rerunCount?: number
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
  onRetry: () => void
  onRerun: () => void
  isRetrying?: boolean
  isRerunning?: boolean
  actionError?: string
}
```

#### Internal Components

**`ErrorDetails.tsx`** - Error information display for failed analyses
**`ActionCardHeader.tsx`** - Card header with status badge and description
**`helpers.ts`** - Helper functions for status checking and labeling

### 3. React Hooks

#### `useRetryAnalysis.ts`
**Location:** `/frontend/src/features/analysis/hooks/useRetryAnalysis.ts`

**Purpose:** React hook for retrying failed analyses

**API Endpoint:** `POST /api/v1/analyze/{id}/retry`

**Returns:**
```typescript
interface UseRetryAnalysisResult {
  retry: () => Promise<AnalysisRetryResponse | null>
  isRetrying: boolean
  error: string | null
  data: AnalysisRetryResponse | null
}
```

**Usage:**
```tsx
const { retry, isRetrying, error } = useRetryAnalysis(analysisId);

<RetryButton
  onRetry={retry}
  isRetrying={isRetrying}
  retryError={error}
/>
```

#### `useRerunAnalysis.ts`
**Location:** `/frontend/src/features/analysis/hooks/useRerunAnalysis.ts`

**Purpose:** React hook for rerunning completed analyses

**API Endpoint:** `POST /api/v1/analyze/{id}/rerun`

**Returns:**
```typescript
interface UseRerunAnalysisResult {
  rerun: () => Promise<AnalysisRerunResponse | null>
  isRerunning: boolean
  error: string | null
  data: AnalysisRerunResponse | null
}
```

**Usage:**
```tsx
const { rerun, isRerunning, error } = useRerunAnalysis(analysisId);

<RerunButton
  onRerun={rerun}
  isRerunning={isRerunning}
  rerunError={error}
/>
```

## API Integration

### Updated Files

#### `api.service.ts`
**Location:** `/frontend/src/services/api.service.ts`

**New Methods:**
```typescript
/**
 * Retry a failed analysis
 * POST /api/v1/analyze/{id}/retry
 */
retryAnalysis: async (analysisId: string): Promise<AnalysisRetryResponse>

/**
 * Rerun a completed analysis with latest AI models/prompts
 * POST /api/v1/analyze/{id}/rerun
 */
rerunAnalysis: async (analysisId: string): Promise<AnalysisRerunResponse>
```

#### `api.ts` (Types)
**Location:** `/frontend/src/types/api.ts`

**New Types:**
```typescript
export interface AnalysisRetryResponse {
  analysis_id: string
  status: AnalysisStatus
  retry_count: number
  sse_endpoint: string
}

export interface AnalysisRerunResponse {
  analysis_id: string
  status: AnalysisStatus
  rerun_count: number
  archived_artifact_id: string | null
  sse_endpoint: string
}
```

## File Structure

```
frontend/src/features/analysis/
├── components/
│   ├── actions/
│   │   ├── RetryButton.tsx          # Retry button component
│   │   ├── RerunButton.tsx          # Rerun button component
│   │   └── index.ts                 # Barrel export
│   └── cards/
│       ├── AnalysisActionsCard.tsx  # Context-aware actions card
│       ├── internal/
│       │   ├── ActionCardHeader.tsx # Card header component
│       │   ├── ErrorDetails.tsx     # Error display component
│       │   ├── helpers.ts           # Helper functions
│       │   └── index.ts             # Barrel export
│       └── index.ts                 # Barrel export
└── hooks/
    ├── useRetryAnalysis.ts          # Retry hook
    └── useRerunAnalysis.ts          # Rerun hook
```

## Design Patterns Used

### 1. Separation of Concerns
- Action buttons (RetryButton, RerunButton) are independent components
- AnalysisActionsCard handles context-aware selection
- Internal components handle specific UI pieces (header, errors)

### 2. Type Safety
- Full TypeScript strict mode compliance
- Comprehensive prop interfaces
- Type-safe API responses

### 3. Error Handling
- Graceful error display at component level
- Error logging via logger service
- User-friendly error messages

### 4. State Management
- React hooks for async operations
- Loading states for better UX
- Error states with automatic display

### 5. Accessibility
- Semantic HTML structure
- ARIA-compliant UI components (shadcn/ui)
- Keyboard navigation support
- Screen reader friendly

### 6. Code Quality
- ESLint compliant
- Biome formatted
- No TypeScript errors
- Well-documented with JSDoc comments

## Backend API Contract

### Retry Endpoint
```
POST /api/v1/analyze/{analysis_id}/retry
```

**Requirements:**
- Analysis must be in failed state (`extraction_failed`, `analysis_failed`, `artifact_failed`, `quality_gate_failed`, `failed`)
- Retry count must be < 3

**Response:**
```json
{
  "analysis_id": "uuid",
  "status": "pending",
  "retry_count": 1,
  "sse_endpoint": "/api/v1/analyze/{id}/stream"
}
```

### Rerun Endpoint
```
POST /api/v1/analyze/{analysis_id}/rerun
```

**Requirements:**
- Analysis must be in `complete` status

**Response:**
```json
{
  "analysis_id": "uuid",
  "status": "analyzing",
  "rerun_count": 1,
  "archived_artifact_id": "uuid",
  "sse_endpoint": "/api/v1/analyze/{id}/stream"
}
```

## Usage Example

### In AnalyzeResult or similar component:

```tsx
import { AnalysisActionsCard } from '@features/analysis/components/cards'
import { useRetryAnalysis, useRerunAnalysis } from '@features/analysis/hooks'

function AnalyzeResult({ analysisId, status }) {
  const { retry, isRetrying, error: retryError } = useRetryAnalysis(analysisId)
  const { rerun, isRerunning, error: rerunError } = useRerunAnalysis(analysisId)

  return (
    <div>
      {/* Other components */}

      <AnalysisActionsCard
        analysisId={analysisId}
        status={status}
        retryCount={analysis.retry_count}
        rerunCount={analysis.rerun_count}
        errorCode={analysis.error_code}
        errorMessage={analysis.error_message}
        failedAtStage={analysis.failed_at_stage}
        onRetry={retry}
        onRerun={rerun}
        isRetrying={isRetrying}
        isRerunning={isRerunning}
        actionError={retryError || rerunError}
      />
    </div>
  )
}
```

## Quality Checks

All code quality checks passing:

```bash
# TypeScript type checking
npm run typecheck  ✓ PASS

# ESLint linting
npm run lint  ✓ PASS

# Biome formatting
npm run format:check  ✓ PASS (4 warnings - unused params, intentional)
```

## Next Steps

1. **Integration:** Add AnalysisActionsCard to AnalyzeResult component
2. **Testing:** Create unit tests for hooks and components
3. **E2E Testing:** Playwright tests for retry/rerun workflows
4. **Documentation:** Update component library/Storybook

## Notes

- All components follow existing project patterns (shadcn/ui, Tailwind CSS, TypeScript)
- Error handling is comprehensive with user-friendly messages
- Loading states provide good UX feedback
- Backend API endpoints already implemented (checked in endpoints.py)
- Database schema already supports retry_count and rerun_count fields
