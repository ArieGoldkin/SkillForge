import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load TutorSession component
const TutorSession = lazy(() =>
  import('@features/tutor').then((m) => ({ default: m.TutorSession }))
)

// TanStack Router automatically infers the 'sessionId' param type from the route path
// Access via: const { sessionId } = Route.useParams() in the component
export const Route = createFileRoute('/tutor/$sessionId')({
  component: () => (
    <LazyRoute>
      <TutorSession />
    </LazyRoute>
  ),
})
