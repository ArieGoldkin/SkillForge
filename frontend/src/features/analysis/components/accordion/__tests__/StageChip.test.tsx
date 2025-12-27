/**
 * Tests for StageChip - Compact inline chip for stage status display
 *
 * Tests cover:
 * - Name truncation for long stage names
 * - Status rendering (complete, running, failed, pending, skipped)
 * - Status icons (checkmark, spinner, X, circle, minus)
 * - Size variants (sm, md)
 * - Accessibility compliance
 * - Framer Motion animations (status transitions, icon changes)
 *
 * Note: Component uses framer-motion for animations, so tests verify:
 * - Semantic rendering (aria-labels, icons) instead of Tailwind classes
 * - AnimatePresence for icon transitions
 * - Accessibility maintained during animations
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { StageName } from '@/schemas/base'

import type { StageStatusEntry } from '../../../hooks/stageConfig'
import { StageChip } from '../StageChip'

// ============================================================================
// Test Fixtures
// ============================================================================

const createStageStatus = (status: StageStatusEntry['status']): StageStatusEntry => ({
  name: 'test_stage' as StageName,
  status,
})

// ============================================================================
// Tests
// ============================================================================

describe('StageChip', () => {
  describe('truncation', () => {
    it('does not truncate names under 18 characters', () => {
      render(<StageChip stageName="tech_compare" status={createStageStatus('complete')} />)

      // "Tech Compare" is 12 characters - should not truncate (limit is 18)
      expect(screen.getByText('Tech Compare')).toBeInTheDocument()
      expect(screen.queryByText(/\.\.\./)).not.toBeInTheDocument()
    })

    it('truncates names over 18 characters with ellipsis or abbreviation', () => {
      render(
        <StageChip
          stageName="implementation_planner_agent"
          status={createStageStatus('complete')}
        />
      )

      // "Implementation Planner Agent" is > 18 chars
      // Should abbreviate to "Implementation P..." or similar
      const chip = screen.getByLabelText(/Implementation Planner Agent: complete/i)
      expect(chip).toBeInTheDocument()
      // Text should be abbreviated
      expect(screen.getByText(/Implementation P\.\.\./i)).toBeInTheDocument()
    })

    it('shows full formatted name in title attribute', () => {
      render(
        <StageChip stageName="implementation_planner" status={createStageStatus('complete')} />
      )

      // Title should show full formatted name and status
      const chip = screen.getByLabelText(/Implementation Planner: complete/i)
      expect(chip).toHaveAttribute('title', 'Implementation Planner: complete')
    })

    it('formats snake_case to Title Case', () => {
      render(<StageChip stageName="content_type" status={createStageStatus('pending')} />)

      expect(screen.getByText('Content Type')).toBeInTheDocument()
    })

    it('handles single word stage names', () => {
      render(<StageChip stageName="embeddings" status={createStageStatus('running')} />)

      expect(screen.getByText('Embeddings')).toBeInTheDocument()
    })
  })

  describe('status rendering', () => {
    it('renders complete status correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('complete')} />)

      // Verify aria-label shows complete status
      const chip = screen.getByLabelText(/Test Stage: complete/i)
      expect(chip).toBeInTheDocument()

      // Verify icon is present (checkmark for complete)
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('renders running status correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('running')} />)

      // Verify aria-label shows running status
      const chip = screen.getByLabelText(/Test Stage: running/i)
      expect(chip).toBeInTheDocument()

      // Verify spinner icon is present
      const icon = chip.querySelector('svg.animate-spin')
      expect(icon).toBeInTheDocument()
    })

    it('renders synthesizing status correctly (treated as running)', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('synthesizing')} />)

      // Synthesizing is mapped to running status
      const chip = screen.getByLabelText(/Test Stage: running/i)
      expect(chip).toBeInTheDocument()

      // Should have spinner icon
      const icon = chip.querySelector('svg.animate-spin')
      expect(icon).toBeInTheDocument()
    })

    it('renders failed status correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('failed')} />)

      // Verify aria-label shows failed status
      const chip = screen.getByLabelText(/Test Stage: failed/i)
      expect(chip).toBeInTheDocument()

      // Verify X icon is present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('renders static_fallback status correctly (treated as failed)', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('static_fallback')} />)

      // static_fallback is mapped to failed status
      const chip = screen.getByLabelText(/Test Stage: failed/i)
      expect(chip).toBeInTheDocument()

      // Should have X icon
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('renders skipped status correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('skipped')} />)

      // Verify aria-label shows skipped status
      const chip = screen.getByLabelText(/Test Stage: skipped/i)
      expect(chip).toBeInTheDocument()

      // Verify minus icon is present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('renders pending status correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('pending')} />)

      // Verify aria-label shows pending status
      const chip = screen.getByLabelText(/Test Stage: pending/i)
      expect(chip).toBeInTheDocument()

      // Verify circle icon is present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('treats undefined status as pending', () => {
      render(<StageChip stageName="test_stage" status={undefined} />)

      // Should render as pending
      const chip = screen.getByLabelText(/Test Stage: pending/i)
      expect(chip).toBeInTheDocument()

      // Should have circle icon
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('status icons', () => {
    it('shows checkmark icon for complete status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('complete')} />)

      // Check for CheckCircle2 icon via aria-hidden
      const chip = screen.getByLabelText(/Test Stage: complete/i)
      expect(chip).toBeInTheDocument()

      // Icon should be present (hidden from screen readers)
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('shows spinner icon for running status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('running')} />)

      const chip = screen.getByLabelText(/Test Stage: running/i)
      expect(chip).toBeInTheDocument()

      // Spinner should have animate-spin class
      const icon = chip.querySelector('svg.animate-spin')
      expect(icon).toBeInTheDocument()
    })

    it('shows X icon for failed status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('failed')} />)

      const chip = screen.getByLabelText(/Test Stage: failed/i)
      expect(chip).toBeInTheDocument()

      // XCircle icon should be present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('shows minus icon for skipped status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('skipped')} />)

      const chip = screen.getByLabelText(/Test Stage: skipped/i)
      expect(chip).toBeInTheDocument()

      // MinusCircle icon should be present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('shows circle icon for pending status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('pending')} />)

      const chip = screen.getByLabelText(/Test Stage: pending/i)
      expect(chip).toBeInTheDocument()

      // Circle icon should be present
      const icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('size variants', () => {
    it('renders small size correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('complete')} size="sm" />)

      // Should render with accessible label
      const chip = screen.getByLabelText(/Test Stage: complete/i)
      expect(chip).toBeInTheDocument()

      // Icon should be present with h-3 w-3 classes
      const icon = chip.querySelector('svg.h-3.w-3')
      expect(icon).toBeInTheDocument()
    })

    it('renders medium size correctly', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('complete')} size="md" />)

      // Should render with accessible label
      const chip = screen.getByLabelText(/Test Stage: complete/i)
      expect(chip).toBeInTheDocument()

      // Icon should be present with h-3.5 w-3.5 classes
      const icon = chip.querySelector('svg.h-3\\.5.w-3\\.5')
      expect(icon).toBeInTheDocument()
    })

    it('defaults to small size when size prop is omitted', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('complete')} />)

      // Should render with accessible label
      const chip = screen.getByLabelText(/Test Stage: complete/i)
      expect(chip).toBeInTheDocument()

      // Should use h-3 w-3 icon (small size)
      const icon = chip.querySelector('svg.h-3.w-3')
      expect(icon).toBeInTheDocument()
    })

    it('uses h-3 w-3 icon for sm size', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} size="sm" />
      )

      const icon = container.querySelector('svg.h-3.w-3')
      expect(icon).toBeInTheDocument()
    })

    it('uses h-3.5 w-3.5 icon for md size', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} size="md" />
      )

      const icon = container.querySelector('svg.h-3\\.5.w-3\\.5')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('has accessible aria-label with stage name and status', () => {
      render(<StageChip stageName="content_type" status={createStageStatus('running')} />)

      expect(screen.getByLabelText('Content Type: running')).toBeInTheDocument()
    })

    it('has title attribute with full formatted name and status', () => {
      render(<StageChip stageName="tech_compare" status={createStageStatus('complete')} />)

      const chip = screen.getByLabelText(/Tech Compare: complete/i)
      // Title uses fullStageName (formatted)
      expect(chip).toHaveAttribute('title', 'Tech Compare: complete')
    })

    it('hides status icon from screen readers', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('failed')} />
      )

      const icon = container.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('provides semantic status information through aria-label', () => {
      render(
        <StageChip stageName="implementation_planner" status={createStageStatus('synthesizing')} />
      )

      // Synthesizing is mapped to "running" status
      expect(screen.getByLabelText(/running/i)).toBeInTheDocument()
    })

    it('handles special statuses correctly in aria-label', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('static_fallback')} />)

      // static_fallback is mapped to "failed" status
      expect(screen.getByLabelText(/failed/i)).toBeInTheDocument()
    })
  })

  describe('text rendering', () => {
    it('truncates chip text with max-w-[120px]', () => {
      const { container } = render(
        <StageChip
          stageName="very_long_stage_name_that_should_be_truncated"
          status={createStageStatus('complete')}
        />
      )

      const text = container.querySelector('span.max-w-\\[120px\\].truncate')
      expect(text).toBeInTheDocument()
    })

    it('preserves text content within truncation limits', () => {
      render(<StageChip stageName="security" status={createStageStatus('complete')} />)

      expect(screen.getByText('Security')).toBeInTheDocument()
    })
  })

  describe('status mapping edge cases', () => {
    it('maps detecting_conflicts to running status', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('detecting_conflicts')} />)

      const chip = screen.getByLabelText(/running/i)
      expect(chip).toBeInTheDocument()
    })

    it('handles all status variants correctly', () => {
      const statuses: Array<StageStatusEntry['status']> = [
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
          <StageChip stageName="test_stage" status={createStageStatus(status)} />
        )

        // Should render without errors
        const chip = screen.getByLabelText(/Test Stage:/i)
        expect(chip).toBeInTheDocument()

        unmount()
      })
    })
  })

  describe('name formatting edge cases', () => {
    it('handles empty string stage name', () => {
      render(<StageChip stageName="" status={createStageStatus('pending')} />)

      // Should not crash, but may render empty
      const chip = screen.getByLabelText(/pending/i)
      expect(chip).toBeInTheDocument()
    })

    it('handles stage name with multiple underscores', () => {
      render(
        <StageChip stageName="extract_key_tech_concepts" status={createStageStatus('complete')} />
      )

      // Should format to "Extract Key Tech Concepts" and truncate to "Extract Ke..."
      const chip = screen.getByLabelText(/Extract Key Tech Concepts: complete/i)
      expect(chip).toBeInTheDocument()
    })

    it('handles already formatted names gracefully', () => {
      // In case a formatted name is passed instead of snake_case
      render(<StageChip stageName="Already Formatted" status={createStageStatus('complete')} />)

      const chip = screen.getByLabelText(/Already Formatted: complete/i)
      expect(chip).toBeInTheDocument()
    })
  })

  describe('animations', () => {
    it('uses motion.span for animated container', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} />
      )

      // motion.span renders as span with framer-motion data attributes
      const chip = container.querySelector('span')
      expect(chip).toBeInTheDocument()

      // Should have accessible label
      const labeledChip = screen.getByLabelText(/Test Stage: complete/i)
      expect(labeledChip).toBeInTheDocument()
    })

    it('wraps icon in motion.div for AnimatePresence', () => {
      render(<StageChip stageName="test_stage" status={createStageStatus('running')} />)

      // Icon should render inside motion.div (via AnimatePresence)
      const chip = screen.getByLabelText(/Test Stage: running/i)
      expect(chip).toBeInTheDocument()

      // Icon wrapper should exist
      const iconWrapper = chip.querySelector('div')
      expect(iconWrapper).toBeInTheDocument()

      // Icon itself should be inside the wrapper
      const icon = iconWrapper?.querySelector('svg.animate-spin')
      expect(icon).toBeInTheDocument()
    })

    it('animates status transitions', () => {
      const { rerender } = render(
        <StageChip stageName="test_stage" status={createStageStatus('running')} />
      )

      // Initially should show running status
      expect(screen.getByLabelText(/Test Stage: running/i)).toBeInTheDocument()

      // Change to complete status
      rerender(<StageChip stageName="test_stage" status={createStageStatus('complete')} />)

      // Should now show complete status
      expect(screen.getByLabelText(/Test Stage: complete/i)).toBeInTheDocument()
    })

    it('handles status icon changes with AnimatePresence', () => {
      const { rerender } = render(
        <StageChip stageName="test_stage" status={createStageStatus('pending')} />
      )

      // Initially should have circle icon (pending)
      let chip = screen.getByLabelText(/Test Stage: pending/i)
      let icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()

      // Change to complete status
      rerender(<StageChip stageName="test_stage" status={createStageStatus('complete')} />)

      // Should now have checkmark icon (complete)
      chip = screen.getByLabelText(/Test Stage: complete/i)
      icon = chip.querySelector('svg[aria-hidden="true"]')
      expect(icon).toBeInTheDocument()
    })

    it('maintains accessibility during animations', () => {
      const { rerender } = render(
        <StageChip stageName="test_stage" status={createStageStatus('running')} />
      )

      // Check initial accessibility
      let chip = screen.getByLabelText(/Test Stage: running/i)
      expect(chip).toHaveAttribute('title')
      expect(chip).toHaveAttribute('aria-label')

      // Change status
      rerender(<StageChip stageName="test_stage" status={createStageStatus('failed')} />)

      // Accessibility attributes should still be present
      chip = screen.getByLabelText(/Test Stage: failed/i)
      expect(chip).toHaveAttribute('title', 'Test Stage: failed')
      expect(chip).toHaveAttribute('aria-label', 'Test Stage: failed')
    })
  })
})
