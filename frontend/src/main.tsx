import { StrictMode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { createRoot } from 'react-dom/client'
// Prism.js syntax highlighting theme
import 'prismjs/themes/prism-tomorrow.css'

import './design-system/prism-custom.css'
import './index.css'
import { router } from './router'
import { initWebVitals } from './services/performance/webVitals.service'
import { logger } from './lib/logger'
import { TIME_CONSTANTS, RETRY_CONSTANTS } from './lib/constants'

// Performance monitoring initialization
if (import.meta.env.DEV) {
  // React Scan for development-time visual performance monitoring
  logger.debug('Initializing React Scan performance monitoring', { service: 'react-scan' })
  import('react-scan')
    .then(({ scan }) => {
      logger.debug('React Scan loaded, starting scan', { service: 'react-scan' })
      scan({
        enabled: true,
        log: true, // Enable console logging for render info
        showToolbar: true, // Show performance toolbar
        trackUnnecessaryRenders: false, // Enable unnecessary render tracking (can be performance intensive)
        animationSpeed: 'fast', // Animation speed for highlights
      })
      logger.info('React Scan initialized successfully', { service: 'react-scan' })
    })
    .catch((error) => {
      logger.error('React Scan failed to initialize', { error, service: 'react-scan' })
    })
}

// Web Vitals for production RUM analytics (works in both dev and prod)
initWebVitals()

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: TIME_CONSTANTS.QUERY_STALE_TIME,
      retry: RETRY_CONSTANTS.QUERY_RETRY_COUNT,
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
