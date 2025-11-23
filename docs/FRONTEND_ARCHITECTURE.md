# Frontend Architecture - SkillForge

**Version:** 1.0
**Last Updated:** November 21, 2025
**Stack:** React 19 + Vite + TypeScript + Tailwind CSS

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
│   │   ├── components/          # Nested components
│   │   ├── hooks/               # Feature-specific hooks
│   │   └── types.ts             # Feature-specific types
│   ├── analysis/
│   ├── tutor/
│   └── library/
│
├── shared/                       # Cross-app reusable code
│   ├── components/
│   │   ├── ui/                  # Base primitives (Button, Card)
│   │   └── layout/              # Layout components (Header, Sidebar)
│   ├── hooks/                   # Shared hooks (useLocalStorage, useDebounce)
│   └── utils/                   # Shared utilities
│
├── store/                        # Global state (Zustand)
├── types/                        # Global TypeScript types
├── lib/                          # Core utilities (cn() function)
├── services/                     # API layer (grouped by domain)
├── router.tsx                    # Route configuration
└── main.tsx                      # App entry point
```

---

## 🎯 Feature Module Structure

Each feature follows this pattern:

```
features/[feature-name]/
├── index.ts                     # Public exports
├── [FeatureName].tsx            # Main component
├── components/                  # Private nested components
│   ├── [Component]A.tsx
│   └── [Component]B.tsx
├── hooks/                       # Private hooks
│   └── use[FeatureName]Data.ts
└── types.ts                     # Private types
```

**Example: Analysis Feature**

```typescript
// features/analysis/index.ts
export { default as AnalyzeResult } from './AnalyzeResult'

// features/analysis/AnalyzeResult.tsx
export default function AnalyzeResult() {
  const data = useAnalysisData()
  return (
    <div>
      <ProgressTracker />
      <AgentFindings />
    </div>
  )
}

// features/analysis/components/ProgressTracker.tsx
export default function ProgressTracker() {
  // Nested component specific to analysis feature
}
```

---

## 🔗 Path Aliases

Use path aliases for clean imports:

```typescript
import { Home } from '@features/home'
import { Button } from '@shared/components/ui/Button'
import { useAppStore } from '@store/useAppStore'
import type { Analysis } from '@types/api'
import { cn } from '@lib/utils'
import { mockAnalyzeAPI } from '@services/mock.service'
```

**Configured aliases:**

- `@/*` → `src/*`
- `@features/*` → `src/features/*`
- `@shared/*` → `src/shared/*`
- `@store/*` → `src/store/*`
- `@types/*` → `src/types/*`
- `@lib/*` → `src/lib/*`
- `@services/*` → `src/services/*`

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
import { useParams } from 'react-router-dom'

import { useAnalysisData } from './hooks/useAnalysisData'
import ProgressTracker from './components/ProgressTracker'
import AgentFindings from './components/AgentFindings'

export default function AnalyzeResult() {
  const { id } = useParams<{ id: string }>()
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

```typescript
// src/router.tsx
const NewFeature = lazy(() =>
  import('@features/new-feature').then((m) => ({ default: m.NewFeature }))
)
```

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
