import { lazy } from 'react'

import { createBrowserRouter } from 'react-router-dom'

import App from './App'
import { LazyRoute } from './router/LazyRoute'

// Lazy load feature modules
const Home = lazy(() => import('@features/home').then((m) => ({ default: m.Home })))
const AnalyzeResult = lazy(() =>
  import('@features/analysis').then((m) => ({ default: m.AnalyzeResult }))
)
const TutorSession = lazy(() =>
  import('@features/tutor').then((m) => ({ default: m.TutorSession }))
)
const Library = lazy(() => import('@features/library').then((m) => ({ default: m.Library })))

export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
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
    ],
  },
])
