# Frontend Architecture - SkillForge

**Version:** 2.0
**Last Updated:** November 26, 2025
**Stack:** React 19 + Vite + TypeScript + Tailwind CSS + TanStack Router

---

## 📐 Architecture Philosophy

SkillForge frontend follows a **feature-based modular architecture** (vertical slice pattern) where code is organized by feature/domain rather than by technical type. This approach improves:

- **Colocation**: Related code lives together
- **Scalability**: Adding features doesn't pollute shared folders
- **Maintainability**: Changes are localized to feature modules
- **Developer Experience**: Clear boundaries and easy navigation

---

## 📁 Folder Structure

```
frontend/src/
├── features/                     # Feature modules (vertical slices)
│   ├── home/
│   │   ├── index.ts             # Export { Home }
│   │   ├── Home.tsx             # Main component (max 180 lines)
│   │   └── components/          # Nested components with barrel exports
│   │       ├── index.ts
│   │       ├── HeroSection.tsx
│   │       ├── FeaturesSection.tsx
│   │       ├── HowItWorksSection.tsx
│   │       ├── FeaturesShowcase.tsx
│   │       └── showcase-data.ts
│   │
│   ├── analysis/
│   │   ├── index.ts
│   │   ├── AnalyzeResult.tsx
│   │   ├── components/          # Grouped by domain
│   │   │   ├── index.ts         # Re-exports all component groups
│   │   │   ├── progress/        # Progress-related components
│   │   │   │   ├── index.ts
│   │   │   │   ├── ProgressTracker.tsx
│   │   │   │   ├── ProgressColumn.tsx
│   │   │   │   ├── StageItem.tsx
│   │   │   │   ├── ConnectionStatus.tsx
│   │   │   │   ├── constants.ts
│   │   │   │   ├── sseNormalizer.ts
│   │   │   │   └── __tests__/
│   │   │   ├── activity/        # Agent activity components
│   │   │   │   ├── index.ts
│   │   │   │   ├── ActivityColumn.tsx
│   │   │   │   └── AgentActivityFeed.tsx
│   │   │   ├── steps/           # Analysis steps components
│   │   │   │   ├── index.ts
│   │   │   │   ├── AnalysisSteps.tsx
│   │   │   │   ├── AnalysisStepList.tsx
│   │   │   │   └── AnalysisProgressCard.tsx
│   │   │   └── states/          # Loading/error states
│   │   │       ├── index.ts
│   │   │       ├── LoadingState.tsx
│   │   │       └── NotFoundState.tsx
│   │   └── hooks/
│   │       └── useMockTimestamps.ts
│   │
│   ├── library/
│   │   ├── index.ts
│   │   ├── Library.tsx
│   │   ├── components/
│   │   │   ├── index.ts
│   │   │   ├── SkillCard/       # Complex component with subfiles
│   │   │   │   ├── index.ts
│   │   │   │   ├── SkillCard.tsx        # Main component
│   │   │   │   ├── SkillCardThumbnail.tsx
│   │   │   │   ├── SkillCardMetadata.tsx
│   │   │   │   ├── SkillCardProgress.tsx
│   │   │   │   ├── SkillCardTags.tsx
│   │   │   │   └── types.ts
│   │   │   ├── SkillFilters/    # Filter components with co-located hooks
│   │   │   │   ├── index.ts
│   │   │   │   ├── SkillFilters.tsx
│   │   │   │   ├── FilterSection.tsx
│   │   │   │   ├── DifficultyFilter.tsx
│   │   │   │   ├── StatusFilter.tsx
│   │   │   │   ├── TagFilter.tsx
│   │   │   │   ├── DurationFilter.tsx
│   │   │   │   ├── CheckboxItem.tsx
│   │   │   │   └── hooks/       # Co-located hooks
│   │   │   │       ├── index.ts
│   │   │   │       ├── useSkillFilters.ts
│   │   │   │       └── __tests__/
│   │   │   ├── SkillGridView.tsx
│   │   │   ├── SkillSearch.tsx
│   │   │   └── ContentGrid.tsx
│   │   └── hooks/               # Feature-level hooks
│   │       ├── index.ts
│   │       ├── useFilteredSkills.ts
│   │       ├── useSkillsData.ts
│   │       └── __tests__/
│   │
│   ├── tutor/
│   │   ├── index.ts
│   │   ├── TutorSession.tsx
│   │   ├── components/
│   │   │   ├── index.ts
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── CodeBlock.tsx
│   │   │   ├── SocraticPrompt.tsx
│   │   │   └── MessagesArea.tsx
│   │   └── hooks/
│   │       └── __tests__/
│   │
│   └── not-found/
│       ├── index.ts
│       └── NotFound.tsx
│
├── routes/                       # TanStack Router - file-based routes
│   ├── __root.tsx               # Root layout (Navigation + theme)
│   ├── index.tsx                # / (Home)
│   ├── library.tsx              # /library
│   ├── analyze.$id.tsx          # /analyze/:id (typed param)
│   ├── tutor.$sessionId.tsx     # /tutor/:sessionId (typed param)
│   └── $.tsx                    # Catch-all 404 route
│
├── shared/                       # Cross-app reusable code
│   ├── components/
│   │   ├── index.ts             # Barrel exports
│   │   ├── ui/                  # Base primitives (shadcn/ui)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── input.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── dialog.tsx
│   │   ├── layout/              # Layout components
│   │   │   ├── index.ts
│   │   │   ├── AppShell.tsx
│   │   │   └── ThemeToggle.tsx
│   │   └── navigation/          # Navigation components
│   │       ├── index.ts
│   │       ├── Navigation.tsx
│   │       ├── NavigationLinks.tsx
│   │       └── NavigationActions.tsx
│   └── hooks/                   # Shared hooks
│
├── hooks/                        # App-level hooks (useSSE, useAnalysis)
│   ├── index.ts
│   ├── useSSE.ts
│   ├── useAnalysis.ts
│   └── __tests__/
│
├── stores/                       # Global state (Zustand)
│   ├── sseStore.ts
│   ├── sseStoreHelpers.ts
│   └── __tests__/
│
├── types/                        # Global TypeScript types
│   ├── api.ts                   # API response types
│   └── sse.ts                   # SSE event types
│
├── lib/                          # Core utilities
│   └── utils.ts                 # cn() function, etc.
│
├── services/                     # API layer
│   └── mock.service.ts          # Mock API for development
│
├── router/                       # Router utilities
│   └── LazyRoute.tsx            # Suspense wrapper
│
├── router.tsx                    # Router configuration
├── routeTree.gen.ts             # Auto-generated (DO NOT EDIT)
└── main.tsx                      # App entry point
```

---

## 🎯 Feature Module Structure

Each feature follows this pattern with **domain-based component grouping**:

```
features/[feature-name]/
├── index.ts                     # Public exports (barrel file)
├── [FeatureName].tsx            # Main component
├── components/                  # Private nested components
│   ├── index.ts                 # Re-exports all components
│   ├── SimpleComponent.tsx      # Simple components at root
│   ├── [ComponentGroup]/        # Complex components in subfolders
│   │   ├── index.ts
│   │   ├── MainComponent.tsx
│   │   ├── SubComponent1.tsx
│   │   ├── SubComponent2.tsx
│   │   ├── types.ts             # Component-specific types
│   │   └── hooks/               # Co-located hooks
│   │       ├── index.ts
│   │       ├── useComponentData.ts
│   │       └── __tests__/
│   └── [domain]/                # Domain-grouped components
│       ├── index.ts
│       └── *.tsx
├── hooks/                       # Feature-level hooks
│   ├── index.ts
│   └── __tests__/
└── types.ts                     # Feature-specific types
```

### Component Organization Patterns

**Pattern 1: Simple Component (single file)**
```
components/
├── SkillSearch.tsx              # < 100 lines, self-contained
└── LoadingGrid.tsx
```

**Pattern 2: Complex Component (subfolder with breakdown)**
```
components/
└── SkillCard/
    ├── index.ts                 # export { SkillCard } from './SkillCard'
    ├── SkillCard.tsx            # Main component (orchestrates subcomponents)
    ├── SkillCardThumbnail.tsx   # Visual subcomponent
    ├── SkillCardMetadata.tsx    # Data display subcomponent
    ├── SkillCardProgress.tsx    # Progress indicator
    ├── SkillCardTags.tsx        # Tags display
    └── types.ts                 # SkillCardProps, etc.
```

**Pattern 3: Component with Co-located Hooks**
```
components/
└── SkillFilters/
    ├── index.ts
    ├── SkillFilters.tsx         # Main filter component
    ├── DifficultyFilter.tsx     # Filter subcomponents
    ├── StatusFilter.tsx
    ├── TagFilter.tsx
    └── hooks/                   # Co-located hooks
        ├── index.ts
        ├── useSkillFilters.ts   # Filter state management
        └── __tests__/
            └── useSkillFilters.test.ts
```

**Pattern 4: Domain-Grouped Components**
```
components/
├── index.ts                     # Re-exports all domains
├── progress/                    # Progress-related components
│   ├── index.ts
│   ├── ProgressTracker.tsx
│   ├── StageItem.tsx
│   └── constants.ts
├── activity/                    # Activity-related components
│   ├── index.ts
│   └── AgentActivityFeed.tsx
└── states/                      # UI states
    ├── index.ts
    ├── LoadingState.tsx
    └── NotFoundState.tsx
```

### Example: Library Feature

```typescript
// features/library/index.ts
export { Library } from './Library'
export * from './components'

// features/library/components/index.ts
export { SkillCard, type SkillCardProps } from './SkillCard'
export { SkillFilters } from './SkillFilters'
export { SkillGridView } from './SkillGridView'
export { SkillSearch } from './SkillSearch'

// features/library/components/SkillCard/index.ts
export { SkillCard } from './SkillCard'
export type { SkillCardProps } from './types'

// features/library/hooks/index.ts
export { useFilteredSkills } from './useFilteredSkills'
export { useSkillsData } from './useSkillsData'
```

---

## 🔗 Path Aliases

Use path aliases for clean imports:

```typescript
import { Home } from '@features/home'
import { Button } from '@shared/components/ui/button'
import { useSSEStore } from '@stores/sseStore'
import type { Analysis } from '@app-types/api'
import { cn } from '@lib/utils'
import { mockAnalyzeAPI } from '@services/mock.service'
import { useSSE } from '@hooks'
import { LazyRoute } from '@router/LazyRoute'
```

**Configured aliases (vite.config.ts & tsconfig.json):**

| Alias | Path | Usage |
|-------|------|-------|
| `@features` | `src/features/*` | Feature modules |
| `@shared` | `src/shared/*` | Shared components/hooks |
| `@stores` | `src/stores/*` | Zustand stores |
| `@hooks` | `src/hooks/*` | App-level hooks |
| `@app-types` | `src/types/*` | TypeScript types (renamed from `@types` to avoid conflict with DefinitelyTyped) |
| `@lib` | `src/lib/*` | Utility functions |
| `@services` | `src/services/*` | API services |
| `@router` | `src/router/*` | Router utilities |

> **Note:** We use `@app-types` instead of `@types` because TypeScript reserves `@types/` for DefinitelyTyped packages.

---

## 📏 Code Quality Rules

### File and Function Limits

| Rule                      | Limit | Enforcement |
| ------------------------- | ----- | ----------- |
| **Max lines per file**    | 180   | Error       |
| **Max lines per function**| 50    | Error       |
| **Cyclomatic complexity** | 15    | Error       |
| **Max nesting depth**     | 4     | Error       |
| **Max function params**   | 4     | Error       |

### React-Specific Rules

| Rule | Description | Enforcement |
|------|-------------|-------------|
| **react/no-array-index-key** | Never use array index as React key | Error |

**Why no array index as key?**
Using array index as key causes React reconciliation issues when items are reordered, deleted, or inserted. Always use stable, unique identifiers.

```typescript
// ❌ Bad - using index as key
{items.map((item, index) => <Item key={index} {...item} />)}

// ✅ Good - using stable ID
{items.map((item) => <Item key={item.id} {...item} />)}

// ✅ Good - pre-process to add stable IDs
const itemsWithIds = React.useMemo(
  () => items.map((content, idx) => ({ id: `item-${idx}`, content })),
  [items]
)
{itemsWithIds.map((item) => <Item key={item.id} {...item} />)}
```

### Why These Limits?

**180 lines per file:**

- Forces component decomposition
- Easier code reviews
- Reduces cognitive load
- Industry best practice (Single Responsibility Principle)

**Complexity 15:**

- Reduces bug likelihood
- Improves testability
- Forces breaking down complex logic
- Based on research (McCabe's Cyclomatic Complexity)

### When Limits Are Exceeded

**Pre-commit hook fails** with error message:

```
✗ src/features/analysis/AnalyzeResult.tsx: File has 215 lines (max 180)
✗ src/features/analysis/hooks/useAnalysisData.ts: Complexity 18 (max 15)
```

**Solution:** Use Code Quality Reviewer agent:

1. Ask: "Help me refactor [filename]"
2. Agent analyzes and suggests:
   - Extract components to `components/` subfolder
   - Move logic to custom hooks
   - Split functions into smaller pieces
   - Reduce complexity patterns

---

## 🏗️ Component Patterns

### Feature Component (Parent)

```typescript
// features/analysis/AnalyzeResult.tsx (main component)
import { useParams } from '@tanstack/react-router'

import { useAnalysisData } from './hooks/useAnalysisData'
import ProgressTracker from './components/ProgressTracker'
import AgentFindings from './components/AgentFindings'

export default function AnalyzeResult() {
  // Type-safe params from TanStack Router route definition
  const { id } = useParams({ from: '/analyze/$id' })  // 'id' is automatically typed!
  const { data, isLoading } = useAnalysisData(id)

  if (isLoading) return <LoadingState />

  return (
    <div className="container">
      <ProgressTracker progress={data.progress} />
      <AgentFindings findings={data.findings} />
    </div>
  )
}
```

### Nested Component (Child)

```typescript
// features/analysis/components/ProgressTracker.tsx
interface Props {
  progress: number
}

export default function ProgressTracker({ progress }: Props) {
  return (
    <div className="p-4 border rounded">
      <div className="h-2 bg-primary" style={{ width: `${progress}%` }} />
    </div>
  )
}
```

### Shared Component

```typescript
// shared/components/ui/Button/Button.tsx
import { cn } from '@lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary'
}

export default function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  return <button className={cn('px-4 py-2 rounded', className)} {...props} />
}
```

---

## 📦 When to Use `features/` vs `shared/`

**Rule of Thumb: Rule of Three**

| Usage                            | Location               |
| -------------------------------- | ---------------------- |
| Used in **1 feature**            | Keep in `features/`    |
| Used in **2 features**           | Keep in `features/`    |
| Used in **3+ features**          | Move to `shared/`      |

**Examples:**

- `ProgressTracker` used only in `analysis` → `features/analysis/components/`
- `Button` used in 5 features → `shared/components/ui/Button/`
- `useLocalStorage` used across app → `shared/hooks/useLocalStorage.ts`

---

## 🎨 Styling Guidelines

### Tailwind CSS

- Use **utility classes** first
- Extract to **component classes** when repeated 3+ times
- Use **`cn()` utility** for conditional classes

```typescript
import { cn } from '@lib/utils'

function Alert({ variant }: { variant: 'info' | 'error' }) {
  return (
    <div
      className={cn(
        'p-4 rounded border',
        variant === 'info' && 'bg-blue-50 border-blue-200',
        variant === 'error' && 'bg-red-50 border-red-200'
      )}
    >
      Alert content
    </div>
  )
}
```

### Design Tokens

Use CSS variables for theme colors (defined in `index.css`):

```typescript
<div className="bg-background text-foreground border-border">
```

---

## 🔄 State Management

### Global State (Zustand)

```typescript
// store/useAppStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  theme: 'light' | 'dark'
  setTheme: (theme: 'light' | 'dark') => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'light',
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'app-storage' }
  )
)
```

### Server State (TanStack Query)

```typescript
// features/analysis/hooks/useAnalysisData.ts
import { useQuery } from '@tanstack/react-query'

import { mockAnalyzeAPI } from '@services/mock.service'

export function useAnalysisData(id: string) {
  return useQuery({
    queryKey: ['analysis', id],
    queryFn: () => mockAnalyzeAPI.getAnalysis(id),
  })
}
```

## 📡 SSE Integration

### Server-Sent Events (SSE) for Real-Time Updates

SkillForge uses Server-Sent Events (SSE) to stream real-time progress updates during analysis workflow execution. The frontend connects to the SSE endpoint and receives progress events as the workflow executes.

**Event Schema:** See [`docs/issues/040-sse-endpoint/SSE_SCHEMA.md`](../docs/issues/040-sse-endpoint/SSE_SCHEMA.md) for complete TypeScript type definitions.

**API Contract:** See [`docs/INTEGRATION_POINTS.md`](../docs/INTEGRATION_POINTS.md) for SSE endpoint details.

### useSSE Hook Pattern

**Recommended implementation:**
```typescript
// features/analysis/hooks/useSSE.ts
import { useEffect, useRef, useState } from 'react'

import type { SSEEvent } from '@types/sse'

interface UseSSEOptions {
  analysisId: string
  onProgress?: (event: SSEEvent) => void
  onComplete?: (event: SSEEvent) => void
  onError?: (event: SSEEvent) => void
}

export function useSSE({ analysisId, onProgress, onComplete, onError }: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!analysisId) return

    const eventSource = new EventSource(
      `/api/v1/analyze/${analysisId}/stream`
    )

    eventSourceRef.current = eventSource
    setIsConnected(true)

    eventSource.addEventListener('progress', (event: MessageEvent) => {
      const data: SSEEvent = JSON.parse(event.data)
      onProgress?.(data)
    })

    eventSource.addEventListener('complete', (event: MessageEvent) => {
      const data: SSEEvent = JSON.parse(event.data)
      onComplete?.(data)
      eventSource.close()
    })

    eventSource.addEventListener('error', (event: MessageEvent) => {
      const data: SSEEvent = JSON.parse(event.data)
      onError?.(data)
      eventSource.close()
    })

    eventSource.onerror = () => {
      console.error('SSE connection error')
      setIsConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [analysisId, onProgress, onComplete, onError])

  return { isConnected }
}
```

### Usage in Components

```typescript
// features/analysis/AnalyzeResult.tsx
import { useSSE } from './hooks/useSSE'
import type { SSEEvent } from '@types/sse'

export default function AnalyzeResult() {
  const { id } = useParams({ from: '/analyze/$id' })
  const [progress, setProgress] = useState<Record<string, string>>({})

  useSSE({
    analysisId: id,
    onProgress: (event: SSEEvent) => {
      if (event.type === 'progress') {
        setProgress((prev) => ({
          ...prev,
          [event.stage]: event.status,
        }))
      }
    },
    onComplete: (event: SSEEvent) => {
      if (event.type === 'complete') {
        // Navigate to artifact view
        navigate({ to: '/library' })
      }
    },
    onError: (event: SSEEvent) => {
      if (event.type === 'error') {
        showError(event.details.error)
      }
    },
  })

  return <ProgressTracker progress={progress} />
}
```

### TypeScript Types

Import SSE types from the schema document:
```typescript
// types/sse.ts (generated from SSE_SCHEMA.md)
export type StageName =
  | 'extraction'
  | 'supervisor_routing'
  | 'tech_comparison'
  | 'security_audit'
  | 'implementation_planning'
  | 'performance_audit'
  | 'code_quality_audit'
  | 'trends_analysis'
  | 'dependencies_analysis'
  | 'aggregation'
  | 'artifact_generation'

export type StageStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface SSEProgressEvent {
  type: 'progress'
  analysis_id: string
  stage: StageName
  status: StageStatus
  timestamp: string
  details?: {
    word_count?: number
    agent?: string
    progress_percent?: number
    [key: string]: unknown
  }
}

export interface SSECompleteEvent {
  type: 'complete'
  analysis_id: string
  stage: 'artifact_generation'
  status: 'complete'
  timestamp: string
  details: {
    artifact_id: string
  }
}

export interface SSEErrorEvent {
  type: 'error'
  analysis_id: string
  stage: string
  status: 'failed'
  timestamp: string
  details: {
    error: string
    error_code?: string
    [key: string]: unknown
  }
}

export type SSEEvent = SSEProgressEvent | SSECompleteEvent | SSEErrorEvent
```

**Note:** For complete type definitions, see [`docs/issues/040-sse-endpoint/SSE_SCHEMA.md`](../docs/issues/040-sse-endpoint/SSE_SCHEMA.md).

---

## 🧪 Testing Strategy

### Test File Location

Place tests **next to** the code being tested:

```
features/analysis/
├── AnalyzeResult.tsx
├── AnalyzeResult.test.tsx      # ✅ Co-located
└── components/
    ├── ProgressTracker.tsx
    └── ProgressTracker.test.tsx
```

### Test Naming

```typescript
// AnalyzeResult.test.tsx
describe('AnalyzeResult', () => {
  it('displays analysis ID from URL params', () => {})
  it('shows loading state while fetching data', () => {})
  it('renders AgentFindings when data is loaded', () => {})
})
```

---

## 📝 File Naming Conventions

| File Type         | Pattern                     | Example                     |
| ----------------- | --------------------------- | --------------------------- |
| **Components**    | `PascalCase.tsx`            | `AnalyzeResult.tsx`         |
| **Hooks**         | `useCamelCase.ts`           | `useAnalysisData.ts`        |
| **Utils**         | `camelCase.ts`              | `formatDate.ts`             |
| **Types**         | `camelCase.types.ts`        | `analysis.types.ts`         |
| **Services**      | `camelCase.service.ts`      | `mock.service.ts`           |
| **Tests**         | `[FileName].test.tsx`       | `AnalyzeResult.test.tsx`    |
| **Index exports** | `index.ts`                  | `features/home/index.ts`    |

---

## 🚀 Development Workflow

### Adding a New Feature

1. **Create feature folder:**

```bash
mkdir -p src/features/new-feature/{components,hooks}
```

2. **Create main component:**

```typescript
// src/features/new-feature/NewFeature.tsx
export default function NewFeature() {
  return <div>New Feature</div>
}
```

3. **Create index export:**

```typescript
// src/features/new-feature/index.ts
export { default as NewFeature } from './NewFeature'
```

4. **Add route:**

Create a new route file in `src/routes/`:

```typescript
// src/routes/new-feature.tsx (creates /new-feature route)
import { lazy } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { LazyRoute } from '@router/LazyRoute'

const NewFeature = lazy(() =>
  import('@features/new-feature').then((m) => ({ default: m.NewFeature }))
)

export const Route = createFileRoute('/new-feature')({
  component: () => (
    <LazyRoute>
      <NewFeature />
    </LazyRoute>
  ),
})
```

**TanStack Router automatically detects the new route file and regenerates `routeTree.gen.ts`.**

### Refactoring Large Components

**If component exceeds 180 lines:**

1. **Extract nested components** to `components/` subfolder
2. **Extract hooks** to `hooks/` subfolder
3. **Extract types** to `types.ts` or `[feature].types.ts`
4. **Simplify logic** - break down complex functions

**Example refactoring:**

Before (220 lines):

```
features/analysis/AnalyzeResult.tsx (220 lines)
```

After (4 files, all < 180 lines):

```
features/analysis/
├── AnalyzeResult.tsx (95 lines)
├── components/
│   ├── ProgressTracker.tsx (45 lines)
│   └── AgentFindings.tsx (65 lines)
└── hooks/
    └── useAnalysisData.ts (35 lines)
```

---

## ✅ Quality Checklist

Before committing code:

- [ ] All files < 180 lines
- [ ] All functions < 50 lines
- [ ] Cyclomatic complexity < 15
- [ ] Imports organized (builtin → external → internal)
- [ ] Path aliases used (`@features`, `@shared`, etc.)
- [ ] TypeScript types defined
- [ ] No console.log (use console.warn/error only)
- [ ] Biome formatting applied
- [ ] ESLint passes with 0 warnings
- [ ] Pre-commit hook passes

---

## 🛠️ Useful Commands

```bash
# Development
npm run dev                    # Start dev server

# Code Quality
npm run lint                   # Check for linting errors
npm run lint:fix               # Auto-fix linting errors
npm run format                 # Format code with Biome
npm run format:check           # Check formatting
npm run quality:check          # Run all quality checks
npm run quality:fix            # Fix all fixable issues

# Build
npm run build                  # Type check + build for production
npm run preview                # Preview production build
```

---

## 🔗 Related Documentation

- [Integration Points](./INTEGRATION_POINTS.md) - API contracts with backend
- [Code Quality Rules](./.claude/instructions/code-quality-rules.md) - ESLint rules explained
- [User Stories](./USER_STORIES.md) - Feature requirements
- [Architecture Overview](./ARCHITECTURE.md) - Full system architecture

---

**Questions?** This architecture is designed for scalability and maintainability. If you're unsure where code should live, ask yourself: "Is this used in one feature or across multiple features?" That's your answer.
