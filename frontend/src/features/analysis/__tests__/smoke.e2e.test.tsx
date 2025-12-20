/**
 * E2E Smoke Tests - December 2025 Best Practices
 *
 * Simple smoke tests to verify components render without crashing.
 * Tagged with @e2e - only runs when E2E_READY=true
 */

import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AnalyzeResult from '../AnalyzeResult'

// Mock dependencies for smoke testing
vi.mock('@tanstack/react-router', () => ({
  getRouteApi: () => ({
    useParams: () => ({ id: 'test-analysis-id' }),
    useSearch: () => ({ completed: false }),
  }),
  useNavigate: () => vi.fn(),
}))

// Only load and run when E2E_READY=true
const conditionalDescribe = process.env.E2E_READY === 'true' ? describe : describe.skip

conditionalDescribe('Smoke Component Tests @component-e2e @critical', () => {
  it('should render AnalyzeResult component without crashing', () => {
    expect(() => {
      render(<AnalyzeResult />)
    }).not.toThrow()
  })
})
