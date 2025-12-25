/**
 * Tests for StageChip - Compact inline chip for stage status display
 *
 * Tests cover:
 * - Name truncation for long stage names
 * - Status colors (complete, running, failed, pending, skipped)
 * - Status icons (checkmark, spinner, X, circle, minus)
 * - Size variants (sm, md)
 * - Accessibility compliance
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

  describe('status colors', () => {
    it('shows green background with white text for complete status', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} />
      )

      const chip = container.querySelector('span.bg-\\[oklch\\(0\\.6959_0\\.1491_162\\.4796\\)\\]')
      expect(chip).toBeInTheDocument()
      expect(chip).toHaveClass('text-white')
    })

    it('shows blue background with white text for running status', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('running')} />
      )

      const chip = container.querySelector('span.bg-\\[oklch\\(0\\.6232_0\\.2118_259\\.1492\\)\\]')
      expect(chip).toBeInTheDocument()
      expect(chip).toHaveClass('text-white')
    })

    it('shows blue background for synthesizing status (treated as running)', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('synthesizing')} />
      )

      const chip = container.querySelector('span.bg-\\[oklch\\(0\\.6232_0\\.2118_259\\.1492\\)\\]')
      expect(chip).toBeInTheDocument()
    })

    it('shows red background with white text for failed status', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('failed')} />
      )

      const chip = container.querySelector('span.bg-\\[oklch\\(0\\.6369_0\\.2077_25\\.3313\\)\\]')
      expect(chip).toBeInTheDocument()
      expect(chip).toHaveClass('text-white')
    })

    it('shows red background for static_fallback status (treated as failed)', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('static_fallback')} />
      )

      const chip = container.querySelector('span.bg-\\[oklch\\(0\\.6369_0\\.2077_25\\.3313\\)\\]')
      expect(chip).toBeInTheDocument()
    })

    it('shows gray background for skipped status', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('skipped')} />
      )

      const chip = container.querySelector(
        'span.bg-\\[oklch\\(0\\.5556_0\\.0001_286\\.3746\\)\\]\\/50'
      )
      expect(chip).toBeInTheDocument()
    })

    it('shows muted gray background for pending status', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('pending')} />
      )

      const chip = container.querySelector(
        'span.bg-\\[oklch\\(0\\.5556_0\\.0001_286\\.3746\\)\\]\\/20'
      )
      expect(chip).toBeInTheDocument()
    })

    it('treats undefined status as pending', () => {
      const { container } = render(<StageChip stageName="test_stage" status={undefined} />)

      const chip = container.querySelector(
        'span.bg-\\[oklch\\(0\\.5556_0\\.0001_286\\.3746\\)\\]\\/20'
      )
      expect(chip).toBeInTheDocument()
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
    it('applies small size classes when size="sm"', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} size="sm" />
      )

      // Improved size: px-2 py-1 text-xs min-h-[24px]
      const chip = container.querySelector('span.px-2.py-1.text-xs.min-h-\\[24px\\]')
      expect(chip).toBeInTheDocument()
    })

    it('applies medium size classes when size="md"', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} size="md" />
      )

      // Medium size: px-3 py-1.5 text-sm min-h-[32px]
      const chip = container.querySelector('span.px-3.py-1\\.5.text-sm.min-h-\\[32px\\]')
      expect(chip).toBeInTheDocument()
    })

    it('defaults to small size when size prop is omitted', () => {
      const { container } = render(
        <StageChip stageName="test_stage" status={createStageStatus('complete')} />
      )

      const chip = container.querySelector('span.px-2.py-1.text-xs.min-h-\\[24px\\]')
      expect(chip).toBeInTheDocument()
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
})
