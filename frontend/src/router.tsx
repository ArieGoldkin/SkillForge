import { lazy, Suspense } from 'react'

import { createBrowserRouter } from 'react-router-dom'

// Lazy load feature modules
const Home = lazy(() => import('@features/home').then((m) => ({ default: m.Home })))
const AnalyzeResult = lazy(() =>
  import('@features/analysis').then((m) => ({ default: m.AnalyzeResult }))
)
const TutorSession = lazy(() =>
  import('@features/tutor').then((m) => ({ default: m.TutorSession }))
)
const Library = lazy(() => import('@features/library').then((m) => ({ default: m.Library })))

// Loading fallback component
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-muted-foreground">Loading...</div>
    </div>
  )
}

// Wrapper for lazy-loaded routes
function LazyRoute({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <LazyRoute>
        <Home />
      </LazyRoute>
    ),
  },
  {
    path: '/analyze/:id',
    element: (
      <LazyRoute>
        <AnalyzeResult />
      </LazyRoute>
    ),
  },
  {
    path: '/tutor/:sessionId',
    element: (
      <LazyRoute>
        <TutorSession />
      </LazyRoute>
    ),
  },
  {
    path: '/library',
    element: (
      <LazyRoute>
        <Library />
      </LazyRoute>
    ),
  },
])
