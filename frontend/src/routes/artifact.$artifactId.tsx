import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load ArtifactPage component from artifact feature
const ArtifactPage = lazy(() =>
  import('@features/artifact').then((m) => ({ default: m.ArtifactPage }))
)

// Search params validation - analysisId for back navigation
interface ArtifactSearchParams {
  analysisId?: string
}

// TanStack Router: /artifact/:artifactId (standalone route)
export const Route = createFileRoute('/artifact/$artifactId')({
  validateSearch: (search: Record<string, unknown>): ArtifactSearchParams => {
    return {
      analysisId: typeof search.analysisId === 'string' ? search.analysisId : undefined,
    }
  },
  component: () => (
    <LazyRoute>
      <ArtifactPage />
    </LazyRoute>
  ),
})
