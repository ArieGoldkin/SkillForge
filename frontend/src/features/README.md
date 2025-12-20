# Features - Feature-Based Frontend Architecture

React 19 + TypeScript application organized by feature modules.

## Structure

```
features/
├── analysis/        # Content analysis feature
│   ├── components/  # Feature-specific components
│   ├── hooks/       # Custom React hooks
│   ├── types/       # TypeScript types
│   ├── utils/       # Utility functions
│   └── __tests__/   # Feature tests
│
├── artifact/        # Artifact viewing/download
│   ├── components/  # Artifact display components
│   ├── hooks/       # useArtifact, etc.
│   └── utils/       # Markdown parsing utilities
│
├── home/            # Home page with library
│   ├── components/  # Library tab, analysis tab
│   └── hooks/       # useLibrary, useAnalyses
│
├── tutor/           # Socratic tutoring chat
│   ├── components/  # Chat UI, message bubbles
│   ├── hooks/       # useTutorSession
│   └── types/       # Tutor message types
│
└── search/          # Semantic search
    ├── components/  # Search bar, results
    └── hooks/       # useSearch
```

## Feature Modules

### Analysis (`features/analysis/`)

**Purpose**: Real-time analysis workflow with SSE progress tracking.

**Key Components:**
- `AnalyzeResult.tsx` - Main analysis page with progress UI
- `ProgressColumn.tsx` - Stage-by-stage progress visualization
- `ActivityColumn.tsx` - Real-time activity feed from SSE events
- `AnalysisCompleteCard.tsx` - Completion state with download CTA

**Hooks:**
- `useAnalysisStatus()` - Poll analysis status
- `useAnalysisProgress()` - Aggregate SSE events into progress state
- `useSSEConnection()` - Low-level SSE connection management

**Routes:**
- `/analyze/:id` - Analysis progress view
- `/analyze/:id?completed=true&artifactId=...` - Completed state

**Related:**
- SSE Store: `@stores/sseStore.ts`
- API Service: `@services/api.service.ts`

### Artifact (`features/artifact/`)

**Purpose**: Display and download generated artifacts.

**Key Components:**
- `ArtifactView.tsx` - Markdown renderer with syntax highlighting
- `ArtifactHeader.tsx` - Title, metadata, download button
- `TableOfContents.tsx` - Auto-generated from markdown headings

**Utils:**
- `markdownHeadingParser.ts` - Extract headings for TOC
- `codeBlockParser.ts` - Extract code blocks with language tags

**Routes:**
- `/artifact/:id` - Standalone artifact view

**Dependencies:**
- `react-markdown` - Markdown rendering
- `prismjs` - Syntax highlighting
- `mermaid` - Diagram rendering

### Home (`features/home/`)

**Purpose**: Landing page with library and quick analysis.

**Key Components:**
- `LibraryTab.tsx` - Browse existing analyses
- `AnalysisTab.tsx` - Create new analysis
- `SearchBar.tsx` - Semantic search integration

**Hooks:**
- `useLibrary()` - Fetch and paginate library items
- `useAnalyze()` - Create new analysis mutation

**Routes:**
- `/` - Home page with tabs

### Tutor (`features/tutor/`)

**Purpose**: Interactive Socratic tutoring sessions.

**Key Components:**
- `TutorChat.tsx` - Chat interface with message history
- `MessageBubble.tsx` - User/tutor message display
- `SyllabusPanel.tsx` - Learning roadmap visualization

**Hooks:**
- `useTutorSession()` - Session management
- `useTutorSSE()` - Real-time tutor responses via SSE

**Routes:**
- `/tutor/:sessionId` - Active tutoring session

**Related:**
- SSE Store: `@stores/sseStore.ts`

### Search (`features/search/`)

**Purpose**: Semantic and hybrid content search.

**Key Components:**
- `SearchBar.tsx` - Search input with autocomplete
- `SearchResults.tsx` - Results list with highlighting
- `SearchFilters.tsx` - Content type, date range filters

**Hooks:**
- `useSearch()` - Execute search with debouncing
- `useSearchFilters()` - Manage filter state

**Search Modes:**
- `semantic` - Vector similarity search
- `keyword` - Full-text search
- `hybrid` - Combined RRF (Reciprocal Rank Fusion)

## Shared Patterns

### Component Structure

```tsx
// Feature component with co-located styles and logic
export function FeatureComponent({ prop }: Props) {
  // Hooks
  const { data, loading } = useFeatureData()

  // Event handlers
  const handleAction = () => { ... }

  // Render
  return (
    <div className="...">
      {/* Component JSX */}
    </div>
  )
}
```

### Custom Hooks

```tsx
// Custom hook for feature-specific logic
export function useFeature() {
  const [state, setState] = useState()

  // Side effects
  useEffect(() => {
    // ...
  }, [dependencies])

  return { state, actions }
}
```

### TypeScript Types

```tsx
// Feature-specific types
export interface FeatureData {
  id: string
  title: string
  content: string
}

export type FeatureStatus = 'idle' | 'loading' | 'success' | 'error'
```

## State Management

### Global State (Zustand)

- `sseStore` - SSE connection and event state
- `themeStore` - Dark/light mode preference
- `useAppStore` - Application-wide state

### Local State (React)

- Component state via `useState`
- Form state via controlled components
- Derived state via `useMemo`

### Server State (TanStack Query)

- API data caching
- Automatic refetching
- Optimistic updates

```tsx
import { useQuery } from '@tanstack/react-query'

const { data, isLoading } = useQuery({
  queryKey: ['analysis', id],
  queryFn: () => fetchAnalysis(id),
})
```

## Testing

### Unit Tests

```bash
npm test -- features/analysis
npm test -- features/artifact
```

### Test Coverage

- `features/analysis/`: 95%+ (16 test files)
- `features/artifact/`: 80%+
- `features/home/`: 85%+
- `features/tutor/`: 75%+

### Testing Library

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

test('renders feature component', async () => {
  render(<FeatureComponent />)

  await waitFor(() => {
    expect(screen.getByText('Expected')).toBeInTheDocument()
  })
})
```

## Styling

### Tailwind CSS

All components use Tailwind utility classes:

```tsx
<div className="flex items-center gap-4 p-6 bg-white dark:bg-gray-900">
  {/* Content */}
</div>
```

### shadcn/ui Components

Radix UI primitives with Tailwind styling:

```tsx
import { Button } from '@components/ui/button'
import { Dialog } from '@components/ui/dialog'
```

## Performance

### Code Splitting

React.lazy for route-based splitting:

```tsx
const AnalyzeResult = lazy(() => import('./features/analysis/AnalyzeResult'))
```

### Memoization

```tsx
const memoizedValue = useMemo(() => computeExpensive(data), [data])
const memoizedCallback = useCallback(() => handleEvent(), [deps])
```

### Virtual Lists

For large datasets (library, search results):

```tsx
import { useVirtualizer } from '@tanstack/react-virtual'
```

## Related Documentation

- [Component Library](../components/ui/README.md)
- [State Management](../stores/README.md)
- [API Integration](../services/README.md)
