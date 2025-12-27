/**
 * Tests for StageItem - Timeline item for stage progress display
 *
 * Tests cover:
 * - Basic rendering with stage name and status badge
 * - Status badge display for each status type (pending, running, complete, failed, skipped)
 * - Running state with agent info and spinner
 * - Error state with error message and error code
 * - Timeline connector visibility (last vs non-last item)
 * - Accessibility compliance (aria-label, role attributes)
 * - Animation presence verification
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { StageStatus } from '@/schemas/sse'

import type { StageState } from '../constants'
import { StageItem } from '../StageItem'

// ============================================================================
// Test Fixtures
// ============================================================================

const createStageState = (overrides: Partial<StageState> = {}): StageState => ({
  name: 'extraction',
  label: 'Content Extraction',
  status: 'pending',
  ...overrides,
})

// ============================================================================
// Tests
// ============================================================================

describe('StageItem', () => {
  describe('basic rendering', () => {
    it('renders with stage name and status badge', () => {
      render(<StageItem stage={createStageState()} isLast={false} />)

      expect(screen.getByText('Content Extraction')).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
    })

    it('uses stage label as heading', () => {
      render(<StageItem stage={createStageState({ label: 'Custom Stage Label' })} isLast={false} />)

      expect(screen.getByRole('heading', { name: 'Custom Stage Label' })).toBeInTheDocument()
    })

    it('has data-testid for stage indicator', () => {
      const { container } = render(<StageItem stage={createStageState()} isLast={false} />)

      const stageIndicator = container.querySelector('[data-testid="stage-indicator"]')
      expect(stageIndicator).toBeInTheDocument()
    })

    it('has data-stage-status attribute', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'running' })} isLast={false} />
      )

      const stageIndicator = container.querySelector('[data-stage-status="running"]')
      expect(stageIndicator).toBeInTheDocument()
    })
  })

  describe('status badge display', () => {
    it('shows "Pending" text for pending status', () => {
      render(<StageItem stage={createStageState({ status: 'pending' })} isLast={false} />)

      expect(screen.getByText('Pending')).toBeInTheDocument()
    })

    it('shows "Running" text for running status', () => {
      render(<StageItem stage={createStageState({ status: 'running' })} isLast={false} />)

      expect(screen.getByText('Running')).toBeInTheDocument()
    })

    it('shows "Complete" text for complete status', () => {
      render(<StageItem stage={createStageState({ status: 'complete' })} isLast={false} />)

      expect(screen.getByText('Complete')).toBeInTheDocument()
    })

    it('shows "Failed" text for failed status', () => {
      render(<StageItem stage={createStageState({ status: 'failed' })} isLast={false} />)

      expect(screen.getByText('Failed')).toBeInTheDocument()
    })

    it('shows "Skipped" text for skipped status', () => {
      render(<StageItem stage={createStageState({ status: 'skipped' })} isLast={false} />)

      expect(screen.getByText('Skipped')).toBeInTheDocument()
    })

    it('has status badge with data-testid="status-text"', () => {
      render(<StageItem stage={createStageState({ status: 'complete' })} isLast={false} />)

      const statusBadge = screen.getByTestId('status-text')
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge).toHaveTextContent('Complete')
    })

    it('handles all status variants correctly', () => {
      const statuses: StageStatus[] = [
        'pending',
        'running',
        'synthesizing',
        'detecting_conflicts',
        'complete',
        'failed',
        'static_fallback',
        'skipped',
      ]

      statuses.forEach((status) => {
        const { unmount } = render(
          <StageItem stage={createStageState({ status })} isLast={false} />
        )

        // Should render without errors
        const statusBadge = screen.getByRole('status')
        expect(statusBadge).toBeInTheDocument()

        unmount()
      })
    })
  })

  describe('running state', () => {
    it('shows agent info with spinner when status is running', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'running',
            agent: 'extraction_agent',
          })}
          isLast={false}
        />
      )

      // Agent name should be formatted
      expect(screen.getByText('Extraction Agent')).toBeInTheDocument()
    })

    it('shows spinner icon when agent is running', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'running',
            agent: 'extraction_agent',
          })}
          isLast={false}
        />
      )

      // Loader2 icon with animate-spin (inside agent info)
      const agentInfo = screen.getByLabelText(/Agent:/)
      const spinner = agentInfo.querySelector('svg.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(spinner).toHaveClass('h-3', 'w-3', 'text-primary')
    })

    it('has aria-label for agent info', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'running',
            agent: 'security_auditor',
          })}
          isLast={false}
        />
      )

      expect(screen.getByLabelText('Agent: Security Auditor')).toBeInTheDocument()
    })

    it('does not show agent info when status is not running', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'complete',
            agent: 'extraction_agent',
          })}
          isLast={false}
        />
      )

      // Agent name should not be visible
      expect(screen.queryByText('Extraction Agent')).not.toBeInTheDocument()
    })

    it('does not show agent info when agent is undefined', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'running',
            agent: undefined,
          })}
          isLast={false}
        />
      )

      // Agent info should not be present (no "Agent: ..." label)
      expect(screen.queryByLabelText(/Agent:/)).not.toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when status is failed', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: 'Connection timeout',
          })}
          isLast={false}
        />
      )

      expect(screen.getByText(/Connection timeout/)).toBeInTheDocument()
    })

    it('shows error code badge when errorCode is provided', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: 'API request failed',
            errorCode: 'NETWORK_ERROR',
          })}
          isLast={false}
        />
      )

      // formatErrorCode converts NETWORK_ERROR to "Network Error"
      expect(screen.getByText('Network Error')).toBeInTheDocument()
    })

    it('has role="alert" for error info', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: 'Something went wrong',
          })}
          isLast={false}
        />
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('has aria-label for error info with stage name', () => {
      render(
        <StageItem
          stage={createStageState({
            label: 'Content Extraction',
            status: 'failed',
            error: 'Parse error',
          })}
          isLast={false}
        />
      )

      expect(screen.getByLabelText('Error in Content Extraction')).toBeInTheDocument()
    })

    it('does not show error info when error is undefined', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: undefined,
          })}
          isLast={false}
        />
      )

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('shows error without error code gracefully', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: 'Generic error',
            errorCode: undefined,
          })}
          isLast={false}
        />
      )

      expect(screen.getByText(/Generic error/)).toBeInTheDocument()
      expect(screen.queryByText('Code:')).not.toBeInTheDocument()
    })
  })

  describe('timeline connector', () => {
    it('shows connector line when not last item', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'complete' })} isLast={false} />
      )

      // Connector line should be present
      const connector = container.querySelector('.absolute.left-\\[9px\\].top-6.bottom-0.w-0\\.5')
      expect(connector).toBeInTheDocument()
    })

    it('does not show connector line when last item', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'complete' })} isLast={true} />
      )

      // Connector line should not be present
      const connector = container.querySelector('.absolute.left-\\[9px\\].top-6.bottom-0.w-0\\.5')
      expect(connector).not.toBeInTheDocument()
    })

    it('shows green connector for completed stages', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'complete' })} isLast={false} />
      )

      const connector = container.querySelector('.bg-green-50')
      expect(connector).toBeInTheDocument()
    })

    it('shows border connector for non-completed stages', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'pending' })} isLast={false} />
      )

      const connector = container.querySelector('.bg-border')
      expect(connector).toBeInTheDocument()
    })

    it('marks connector as decorative with aria-hidden', () => {
      const { container } = render(<StageItem stage={createStageState()} isLast={false} />)

      const connector = container.querySelector('.absolute.left-\\[9px\\].top-6.bottom-0.w-0\\.5')
      expect(connector).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('accessibility', () => {
    it('has role="listitem" on container', () => {
      render(<StageItem stage={createStageState()} isLast={false} />)

      expect(screen.getByRole('listitem')).toBeInTheDocument()
    })

    it('has aria-label with stage name and status', () => {
      render(
        <StageItem
          stage={createStageState({
            label: 'Security Audit',
            status: 'running',
          })}
          isLast={false}
        />
      )

      expect(screen.getByLabelText('Security Audit: Running')).toBeInTheDocument()
    })

    it('has role="status" on badge', () => {
      render(<StageItem stage={createStageState({ status: 'complete' })} isLast={false} />)

      const badge = screen.getByRole('status')
      expect(badge).toBeInTheDocument()
      expect(badge).toHaveTextContent('Complete')
    })

    it('marks status icon as decorative with aria-hidden', () => {
      const { container } = render(
        <StageItem stage={createStageState({ status: 'complete' })} isLast={false} />
      )

      // Status icon should be aria-hidden
      const icons = container.querySelectorAll('svg[aria-hidden="true"]')
      expect(icons.length).toBeGreaterThan(0)
    })

    it('has aria-describedby linking badge to stage heading', () => {
      render(
        <StageItem
          stage={createStageState({
            name: 'extraction',
            label: 'Content Extraction',
          })}
          isLast={false}
        />
      )

      const badge = screen.getByRole('status')
      expect(badge).toHaveAttribute('aria-describedby', 'stage-extraction')

      const heading = screen.getByRole('heading')
      expect(heading).toHaveAttribute('id', 'stage-extraction')
    })
  })

  describe('animation presence', () => {
    it('wraps status badge in AnimatePresence with motion.div', () => {
      render(<StageItem stage={createStageState({ status: 'complete' })} isLast={false} />)

      // Badge should be wrapped in motion.div
      const statusBadge = screen.getByTestId('status-text')
      expect(statusBadge).toBeInTheDocument()

      // Parent should be a div (motion.div renders as div)
      const parent = statusBadge.parentElement
      expect(parent?.tagName).toBe('DIV')
    })

    it('wraps agent info in AnimatePresence', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'running',
            agent: 'extraction_agent',
          })}
          isLast={false}
        />
      )

      // Agent info should be present
      const agentInfo = screen.getByLabelText(/Agent:/)
      expect(agentInfo).toBeInTheDocument()

      // Should be a div (motion.div)
      expect(agentInfo.tagName).toBe('DIV')
    })

    it('wraps error info in AnimatePresence', () => {
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            error: 'Test error',
          })}
          isLast={false}
        />
      )

      // Error alert should be present
      const errorAlert = screen.getByRole('alert')
      expect(errorAlert).toBeInTheDocument()

      // Should be a div (motion.div)
      expect(errorAlert.tagName).toBe('DIV')
    })
  })

  describe('edge cases', () => {
    it('handles stage without label gracefully', () => {
      render(
        <StageItem
          stage={createStageState({
            label: '',
          })}
          isLast={false}
        />
      )

      // Should render without crashing
      expect(screen.getByRole('listitem')).toBeInTheDocument()
    })

    it('handles all props at once (failed + agent + error)', () => {
      // When failed, error should be shown even if agent is present
      render(
        <StageItem
          stage={createStageState({
            status: 'failed',
            agent: 'test_agent',
            error: 'Previous error',
            errorCode: 'EXTRACTION_FAILED',
          })}
          isLast={false}
        />
      )

      // Error should be visible (status is failed)
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/Previous error/)).toBeInTheDocument()

      // Agent info should not be visible (only shows when running)
      expect(screen.queryByLabelText(/Agent:/)).not.toBeInTheDocument()
    })

    it('renders different stages with different statuses', () => {
      const { rerender } = render(
        <StageItem stage={createStageState({ status: 'pending' })} isLast={false} />
      )

      expect(screen.getByText('Pending')).toBeInTheDocument()

      rerender(
        <StageItem
          stage={createStageState({ status: 'running', agent: 'test_agent' })}
          isLast={false}
        />
      )

      // Animation may show both badges during transition
      // Just verify the component rerenders without errors
      expect(screen.getByRole('listitem')).toBeInTheDocument()
      expect(screen.getByLabelText(/Content Extraction: Running/i)).toBeInTheDocument()

      rerender(<StageItem stage={createStageState({ status: 'complete' })} isLast={false} />)

      expect(screen.getByRole('listitem')).toBeInTheDocument()
      expect(screen.getByLabelText(/Content Extraction: Complete/i)).toBeInTheDocument()
    })
  })
})
