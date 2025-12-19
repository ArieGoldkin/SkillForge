import { StrictMode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { createRoot } from 'react-dom/client'

// Prism.js syntax highlighting theme
import 'prismjs/themes/prism-tomorrow.css'
import './design-system/prism-custom.css'

import './index.css'
import { router } from './router'

// Performance monitoring initialization
if (import.meta.env.DEV) {
  // React Scan for development-time visual performance monitoring
  console.log('🔍 Initializing React Scan performance monitoring...')
  import('react-scan')
    .then(({ scan }) => {
      console.log('✅ React Scan loaded, starting scan...')
      scan({
        enabled: true,
        log: true, // Enable console logging for render info
        showToolbar: true, // Show performance toolbar
        trackUnnecessaryRenders: false, // Enable unnecessary render tracking (can be performance intensive)
        animationSpeed: 'fast', // Animation speed for highlights
      })
      console.log('🚀 React Scan initialized successfully!')
    })
    .catch((error) => {
      console.error('❌ React Scan failed to initialize:', error)
    })
}

// Web Vitals for production RUM analytics (works in both dev and prod)
import { initWebVitals } from './services/performance/webVitals.service'
initWebVitals()

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
)
