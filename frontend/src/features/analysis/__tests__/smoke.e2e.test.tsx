/**
 * E2E Smoke Tests - December 2025 Best Practices
 *
 * Simple smoke tests to verify components render without crashing.
 * These tests run when E2E_READY=true and validate basic functionality.
 */

import { environmentCapabilities } from '@test-utils/environment'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AnalyzeResult from '../AnalyzeResult'

// Mock all complex dependencies for simple smoke testing
vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }),
  useNavigate: () => vi.fn(),
  useRouter: () => ({
    navigate: vi.fn(),
  }),
}))

vi.mock('../hooks/useAnalysisProgress', () => ({
  useAnalysisProgress: () => ({
    overallProgress: { stage: 'waiting', progress: 0 },
    steps: [],
    activities: [],
    hasError: false,
    errorMessage: null,
    artifactId: null,
    hasFailedStages: false,
    failedStagesCount: 0,
    analysisMetadata: {
      title: 'Test Analysis',
      url: 'https://example.com',
      contentType: 'article',
      wordCount: 1000,
    },
  }),
}))

vi.mock('../hooks/useAnalysisStatus', () => ({
  useAnalysisStatus: () => ({
    resolvedStatus: null,
    resolvedArtifactId: null,
    shouldConnect: false,
    loading: false,
    statusError: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@stores/sseStore', () => ({
  useSSEStore: () => ({
    events: [],
    isConnected: false,
    isComplete: false,
    error: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
    reset: vi.fn(),
  }),
  useLoadingState: () => 'waiting_for_events',
  useConnectionMessage: () => 'Disconnected',
  useShowTimeoutWarning: () => false,
  useAnalysisPhase: () => 'waiting',
  useShouldShowProgress: () => false,
}))

// Conditional test suite execution based on environment capabilities
if (environmentCapabilities.e2eReady) {
  describe('E2E Smoke Tests - 2025 Best Practices', () => {
    it('renders AnalyzeResult component without crashing', () => {
      // Simple smoke test to verify component renders
      expect(() => {
        render(<AnalyzeResult />)
      }).not.toThrow()

      // Verify basic structure is present
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })

    it('displays analysis header correctly', () => {
      render(<AnalyzeResult />)

      // Should show title from mocked metadata
      expect(screen.getByText('Test Analysis')).toBeInTheDocument()
      expect(screen.getByText('https://example.com')).toBeInTheDocument()
    })

    it('handles route parameters gracefully', () => {
      render(<AnalyzeResult />)

      // Component should render with mocked route parameters
      expect(screen.getByTestId('common-analysis-layout')).toBeInTheDocument()
    })

    it('shows loading state display', () => {
      render(<AnalyzeResult />)

      // Should show the loading state display component
      expect(screen.getByTestId('loading-state-display')).toBeInTheDocument()
    })
  })
} else {
  // Skip notification when E2E_READY is not set
  console.log('✅ E2E smoke tests skipped: Set E2E_READY=true to enable E2E validation tests')
}
