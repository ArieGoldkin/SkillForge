import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load AnalyzeResult component
const AnalyzeResult = lazy(() =>
  import('@features/analysis').then((m) => ({ default: m.AnalyzeResult }))
)

// Search params for completed analysis state
interface AnalyzeSearchParams {
  completed?: boolean
  artifactId?: string
}

// TanStack Router automatically infers the 'id' param type from the route path
// Access via: const { id } = Route.useParams() in the component
export const Route = createFileRoute('/analyze/$id')({
  validateSearch: (search: Record<string, unknown>): AnalyzeSearchParams => {
    return {
      completed: search.completed === 'true' || search.completed === true,
      artifactId: typeof search.artifactId === 'string' ? search.artifactId : undefined,
    }
  },
  component: () => (
    <LazyRoute>
      <AnalyzeResult />
    </LazyRoute>
  ),
})
