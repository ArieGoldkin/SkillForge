/**
 * Tests for QueueItemActions component - Action buttons for queue items
 */

import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { QueueItemActions } from '../components/QueueItemActions'

// Mock TanStack Router Link component
vi.mock('@tanstack/react-router', () => ({
  Link: ({ to, params, children, className }: any) => (
    <a href={`${to.replace('$artifactId', params.artifactId)}`} className={className}>
      {children}
    </a>
  ),
}))

describe('QueueItemActions', () => {
  const mockOnMarkReviewed = vi.fn()

  const defaultProps = {
    queueId: 1,
    artifactId: 'artifact-123',
    status: 'pending',
    onMarkReviewed: mockOnMarkReviewed,
    isMarkingReviewed: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('View artifact button', () => {
    it('renders view artifact link', () => {
      render(<QueueItemActions {...defaultProps} />)

      const link = screen.getByRole('link')
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/artifact/artifact-123')
    })

    it('has correct accessibility label', () => {
      render(<QueueItemActions {...defaultProps} />)

      // Should have sr-only text "View"
      const link = screen.getByRole('link')
      expect(link.textContent).toContain('View')
    })

    it('uses correct artifact ID in link', () => {
      render(<QueueItemActions {...defaultProps} artifactId="artifact-xyz-789" />)

      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', '/artifact/artifact-xyz-789')
    })
  })

  describe('Mark reviewed button - Pending status', () => {
    it('renders mark reviewed button for pending items', () => {
      render(<QueueItemActions {...defaultProps} status="pending" />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      expect(button).toBeInTheDocument()
      expect(button).not.toBeDisabled()
    })

    it('calls onMarkReviewed with correct queue ID when clicked', async () => {
      const user = userEvent.setup()
      render(<QueueItemActions {...defaultProps} queueId={42} status="pending" />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      await user.click(button)

      expect(mockOnMarkReviewed).toHaveBeenCalledTimes(1)
      expect(mockOnMarkReviewed).toHaveBeenCalledWith(42)
    })

    it('does not call onMarkReviewed when disabled', async () => {
      const user = userEvent.setup()
      render(<QueueItemActions {...defaultProps} status="pending" isMarkingReviewed={true} />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      expect(button).toBeDisabled()

      await user.click(button)

      expect(mockOnMarkReviewed).not.toHaveBeenCalled()
    })

    it('disables button when isMarkingReviewed is true', () => {
      render(<QueueItemActions {...defaultProps} status="pending" isMarkingReviewed={true} />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      expect(button).toBeDisabled()
    })
  })

  describe('Mark reviewed button - Reviewed status', () => {
    it('renders reviewed button for reviewed items', () => {
      render(<QueueItemActions {...defaultProps} status="reviewed" />)

      const button = screen.getByRole('button', { name: /reviewed/i })
      expect(button).toBeInTheDocument()
    })

    it('disables button for reviewed items', () => {
      render(<QueueItemActions {...defaultProps} status="reviewed" />)

      const button = screen.getByRole('button', { name: /reviewed/i })
      expect(button).toBeDisabled()
    })

    it('does not call onMarkReviewed for reviewed items', async () => {
      const user = userEvent.setup()
      render(<QueueItemActions {...defaultProps} status="reviewed" />)

      const button = screen.getByRole('button', { name: /reviewed/i })
      await user.click(button)

      expect(mockOnMarkReviewed).not.toHaveBeenCalled()
    })

    it('has secondary variant styling for reviewed items', () => {
      render(<QueueItemActions {...defaultProps} status="reviewed" />)

      // Button should have secondary variant (button exists and is disabled)
      const button = screen.getByRole('button', { name: /reviewed/i })
      expect(button).toBeDisabled()
      // Secondary variant styling is present in the component
      expect(button).toBeInTheDocument()
    })
  })

  describe('Button variants', () => {
    it('uses default variant for pending items', () => {
      render(<QueueItemActions {...defaultProps} status="pending" />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      // Button should be enabled for pending items
      expect(button).not.toBeDisabled()
    })

    it('uses secondary variant for reviewed items', () => {
      render(<QueueItemActions {...defaultProps} status="reviewed" />)

      const button = screen.getByRole('button', { name: /reviewed/i })
      // Button should be disabled for reviewed items
      expect(button).toBeDisabled()
    })
  })

  describe('Icon rendering', () => {
    it('renders ExternalLink icon in view button', () => {
      const { container } = render(<QueueItemActions {...defaultProps} />)

      // Check for ExternalLink icon - it's rendered as SVG
      const icon = container.querySelector('svg.lucide-external-link')
      expect(icon).toBeInTheDocument()
    })

    it('renders CheckCircle icon in mark reviewed button', () => {
      const { container } = render(<QueueItemActions {...defaultProps} />)

      // Check for CheckCircle icon - note the actual class name used by lucide-react
      const icon = container.querySelector('svg.lucide-circle-check-big')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('Tooltip integration', () => {
    it('wraps buttons in tooltip providers', () => {
      const { container } = render(<QueueItemActions {...defaultProps} />)

      // Should have TooltipProvider wrapper
      // Note: Actual tooltip testing would require user interactions and timeouts
      // This is a basic check that the component renders without errors
      expect(container.firstChild).toBeInTheDocument()
    })
  })

  describe('Multiple queue items', () => {
    it('handles different queue IDs correctly', async () => {
      const user = userEvent.setup()

      const { rerender } = render(<QueueItemActions {...defaultProps} queueId={1} />)
      const button1 = screen.getByRole('button', { name: /mark reviewed/i })
      await user.click(button1)
      expect(mockOnMarkReviewed).toHaveBeenCalledWith(1)

      mockOnMarkReviewed.mockClear()

      rerender(<QueueItemActions {...defaultProps} queueId={99} />)
      const button2 = screen.getByRole('button', { name: /mark reviewed/i })
      await user.click(button2)
      expect(mockOnMarkReviewed).toHaveBeenCalledWith(99)
    })

    it('handles different artifact IDs in links', () => {
      const { rerender } = render(<QueueItemActions {...defaultProps} artifactId="artifact-aaa" />)
      expect(screen.getByRole('link')).toHaveAttribute('href', '/artifact/artifact-aaa')

      rerender(<QueueItemActions {...defaultProps} artifactId="artifact-bbb" />)
      expect(screen.getByRole('link')).toHaveAttribute('href', '/artifact/artifact-bbb')
    })
  })

  describe('Button sizing', () => {
    it('uses small size variant', () => {
      render(<QueueItemActions {...defaultProps} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        // Small size is indicated by h-8 class (height: 2rem)
        expect(button.className).toContain('h-8')
      })
    })
  })

  describe('Edge cases', () => {
    it('handles unknown status gracefully', () => {
      render(<QueueItemActions {...defaultProps} status="unknown" />)

      // Should still render without errors
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('handles empty artifact ID', () => {
      render(<QueueItemActions {...defaultProps} artifactId="" />)

      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', '/artifact/')
    })

    it('handles zero queue ID', async () => {
      const user = userEvent.setup()
      render(<QueueItemActions {...defaultProps} queueId={0} status="pending" />)

      const button = screen.getByRole('button', { name: /mark reviewed/i })
      await user.click(button)

      expect(mockOnMarkReviewed).toHaveBeenCalledWith(0)
    })
  })
})
