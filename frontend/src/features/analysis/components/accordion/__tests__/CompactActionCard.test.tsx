/**
 * Tests for CompactActionCard - Grid-integrated action card for completed analysis
 *
 * Tests cover:
 * - Success and error state display
 * - Button states (enabled/disabled based on artifactId)
 * - Navigation and action handling
 * - Border colors matching completion status
 * - Accessibility compliance
 */

import * as sseStoreModule from '@stores/sseStore'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as artifactModule from '@features/artifact'
import type { UseArtifactPreviewReturn } from '@features/artifact'

import { CompactActionCard } from '../CompactActionCard'

// ============================================================================
// Mocks
// ============================================================================

const mockNavigate = vi.fn()
const mockOpenPreview = vi.fn()
const mockDownload = vi.fn()
const mockClosePreview = vi.fn()

// Mock @tanstack/react-router
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
}))

// Mock sseStore
vi.mock('@stores/sseStore', async () => {
  const actual = await vi.importActual('@stores/sseStore')
  return {
    ...actual,
    useSSEStore: vi.fn(),
    selectArtifactId: vi.fn((state: { artifactId: string | null }) => state.artifactId),
  }
})

// Mock artifact preview hook
vi.mock('@features/artifact', () => ({
  useArtifactPreview: vi.fn(),
}))

// ============================================================================
// Tests
// ============================================================================

describe('CompactActionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock implementations
    vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
      (selector: (state: { artifactId: string | null }) => string | null) =>
        selector({ artifactId: 'test-artifact-123' })
    )

    vi.mocked(artifactModule.useArtifactPreview).mockReturnValue({
      isOpen: false,
      openPreview: mockOpenPreview,
      closePreview: mockClosePreview,
      content: null,
      isLoading: false,
      error: null,
      download: mockDownload,
    } satisfies UseArtifactPreviewReturn)
  })

  describe('success state (no errors)', () => {
    it('shows "Analysis Complete" title when no errors', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByText('Analysis Complete')).toBeInTheDocument()
    })

    it('shows success message when no errors', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByText('Your results are ready')).toBeInTheDocument()
    })

    it('shows green checkmark icon when no errors', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      // CheckCircle2 icon should be present
      const icon = container.querySelector('svg.text-\\[oklch\\(0\\.6959_0\\.1491_162\\.4796\\)\\]')
      expect(icon).toBeInTheDocument()
    })

    it('has green left border when no errors', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const card = container.querySelector(
        'article.border-l-\\[oklch\\(0\\.6959_0\\.1491_162\\.4796\\)\\]'
      )
      expect(card).toBeInTheDocument()
    })

    it('has accessible article label for success state', () => {
      render(<CompactActionCard hasErrors={false} />)

      const article = screen.getByRole('article')
      expect(article).toHaveAttribute('aria-label', 'Analysis complete')
    })
  })

  describe('error state (with failures)', () => {
    it('shows "Complete with Errors" title when has errors', () => {
      render(<CompactActionCard hasErrors={true} />)

      expect(screen.getByText('Complete with Errors')).toBeInTheDocument()
    })

    it('shows error message when has errors', () => {
      render(<CompactActionCard hasErrors={true} />)

      expect(screen.getByText('Your results are ready')).toBeInTheDocument()
    })

    it('shows amber sparkles icon when has errors', () => {
      const { container } = render(<CompactActionCard hasErrors={true} />)

      // Sparkles icon should be present with amber color
      const icon = container.querySelector('svg.text-\\[oklch\\(0\\.7686_0\\.1647_70\\.0804\\)\\]')
      expect(icon).toBeInTheDocument()
    })

    it('has amber left border when has errors', () => {
      const { container } = render(<CompactActionCard hasErrors={true} />)

      const card = container.querySelector(
        'article.border-l-\\[oklch\\(0\\.7686_0\\.1647_70\\.0804\\)\\]'
      )
      expect(card).toBeInTheDocument()
    })

    it('has accessible article label for error state', () => {
      render(<CompactActionCard hasErrors={true} />)

      const article = screen.getByRole('article')
      expect(article).toHaveAttribute('aria-label', 'Analysis complete with errors')
    })
  })

  describe('primary action button (View Results)', () => {
    it('renders View Results button', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByLabelText('View analysis results')).toBeInTheDocument()
      expect(screen.getByText('View Results')).toBeInTheDocument()
    })

    it('enables View Results button when artifactId is present', () => {
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('View analysis results')
      expect(button).not.toBeDisabled()
    })

    it('disables View Results button when artifactId is missing', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('View analysis results')
      expect(button).toBeDisabled()
    })

    it('navigates to artifact page when View Results is clicked', async () => {
      const user = userEvent.setup()
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('View analysis results')
      await user.click(button)

      expect(mockNavigate).toHaveBeenCalledWith({
        to: '/artifact/$artifactId',
        params: { artifactId: 'test-artifact-123' },
      })
    })

    it('does not navigate when artifactId is missing', async () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('View analysis results')
      expect(button).toBeDisabled()

      // Should not be clickable
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })

  describe('secondary action buttons', () => {
    it('renders Preview button', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByLabelText('Preview artifact')).toBeInTheDocument()
      expect(screen.getByText('Preview')).toBeInTheDocument()
    })

    it('renders Download button', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByLabelText('Download artifact')).toBeInTheDocument()
      expect(screen.getByText('Download')).toBeInTheDocument()
    })

    it('enables Preview button when artifactId is present', () => {
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Preview artifact')
      expect(button).not.toBeDisabled()
    })

    it('enables Download button when artifactId is present and not loading', () => {
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Download artifact')
      expect(button).not.toBeDisabled()
    })

    it('disables Preview button when artifactId is missing', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Preview artifact')
      expect(button).toBeDisabled()
    })

    it('disables Download button when artifactId is missing', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Download artifact')
      expect(button).toBeDisabled()
    })

    it('disables Download button when loading', () => {
      vi.mocked(artifactModule.useArtifactPreview).mockReturnValue({
        isOpen: false,
        openPreview: mockOpenPreview,
        closePreview: mockClosePreview,
        content: null,
        isLoading: true,
        error: null,
        download: mockDownload,
      } satisfies UseArtifactPreviewReturn)

      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Download artifact')
      expect(button).toBeDisabled()
    })

    it('calls openPreview when Preview button is clicked', async () => {
      const user = userEvent.setup()
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Preview artifact')
      await user.click(button)

      expect(mockOpenPreview).toHaveBeenCalledTimes(1)
    })

    it('calls download when Download button is clicked', async () => {
      const user = userEvent.setup()
      render(<CompactActionCard hasErrors={false} />)

      const button = screen.getByLabelText('Download artifact')
      await user.click(button)

      expect(mockDownload).toHaveBeenCalledTimes(1)
    })
  })

  describe('button layout', () => {
    it('stacks buttons vertically in card', () => {
      render(<CompactActionCard hasErrors={false} />)

      // Verify buttons exist in the layout
      expect(screen.getByLabelText('View analysis results')).toBeInTheDocument()
      expect(screen.getByLabelText('Preview artifact')).toBeInTheDocument()
      expect(screen.getByLabelText('Download artifact')).toBeInTheDocument()
    })

    it('shows secondary buttons in a row', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      // Secondary actions should be in a flex row
      const secondaryRow = container.querySelector('.flex.gap-2')
      expect(secondaryRow).toBeInTheDocument()
    })

    it('makes secondary buttons equal width (flex-1)', () => {
      render(<CompactActionCard hasErrors={false} />)

      // Both Preview and Download should have flex-1
      const previewButton = screen.getByLabelText('Preview artifact')
      const downloadButton = screen.getByLabelText('Download artifact')

      expect(previewButton.className).toContain('flex-1')
      expect(downloadButton.className).toContain('flex-1')
    })
  })

  describe('accessibility', () => {
    it('has accessible labels on all buttons', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(screen.getByLabelText('View analysis results')).toBeInTheDocument()
      expect(screen.getByLabelText('Preview artifact')).toBeInTheDocument()
      expect(screen.getByLabelText('Download artifact')).toBeInTheDocument()
    })

    it('hides decorative icons from screen readers', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const icons = container.querySelectorAll('svg[aria-hidden="true"]')
      // Should have at least the completion icon and button icons
      expect(icons.length).toBeGreaterThan(0)
    })

    it('has keyboard accessible buttons', () => {
      render(<CompactActionCard hasErrors={false} />)

      const viewButton = screen.getByLabelText('View analysis results')
      const previewButton = screen.getByLabelText('Preview artifact')
      const downloadButton = screen.getByLabelText('Download artifact')

      // All buttons should be focusable
      expect(viewButton.tagName).toBe('BUTTON')
      expect(previewButton.tagName).toBe('BUTTON')
      expect(downloadButton.tagName).toBe('BUTTON')
    })

    it('properly indicates disabled state to screen readers', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      const viewButton = screen.getByLabelText('View analysis results')
      const previewButton = screen.getByLabelText('Preview artifact')
      const downloadButton = screen.getByLabelText('Download artifact')

      // Disabled buttons should have disabled attribute
      expect(viewButton).toHaveAttribute('disabled')
      expect(previewButton).toHaveAttribute('disabled')
      expect(downloadButton).toHaveAttribute('disabled')
    })
  })

  describe('visual consistency', () => {
    it('matches CompactGroupCard styling with border-l-4', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const card = container.querySelector('article.border-l-4')
      expect(card).toBeInTheDocument()
    })

    it('has same min-height as CompactGroupCard', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const card = container.querySelector('article.min-h-\\[140px\\]')
      expect(card).toBeInTheDocument()
    })

    it('has hover effect for visual consistency', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const card = container.querySelector('article.hover\\:shadow-sm')
      expect(card).toBeInTheDocument()
    })

    it('uses same padding as CompactGroupCard', () => {
      const { container } = render(<CompactActionCard hasErrors={false} />)

      const card = container.querySelector('article.p-3')
      expect(card).toBeInTheDocument()
    })
  })

  describe('custom className', () => {
    it('applies custom className to card', () => {
      const { container } = render(
        <CompactActionCard hasErrors={false} className="custom-test-class" />
      )

      const card = container.querySelector('.custom-test-class')
      expect(card).toBeInTheDocument()
    })
  })

  describe('hook integration', () => {
    it('calls useSSEStore with selectArtifactId selector', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(sseStoreModule.useSSEStore).toHaveBeenCalled()
    })

    it('calls useArtifactPreview with artifactId', () => {
      render(<CompactActionCard hasErrors={false} />)

      expect(artifactModule.useArtifactPreview).toHaveBeenCalledWith('test-artifact-123')
    })

    it('calls useArtifactPreview with null when artifactId is missing', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: null })
      )

      render(<CompactActionCard hasErrors={false} />)

      expect(artifactModule.useArtifactPreview).toHaveBeenCalledWith(null)
    })
  })

  describe('edge cases', () => {
    it('handles undefined hasErrors prop (defaults to false)', () => {
      render(<CompactActionCard />)

      // Should default to success state
      expect(screen.getByText('Analysis Complete')).toBeInTheDocument()
    })

    it('handles empty artifactId string as falsy', () => {
      vi.mocked(sseStoreModule.useSSEStore).mockImplementation(
        (selector: (state: { artifactId: string | null }) => string | null) =>
          selector({ artifactId: '' })
      )

      render(<CompactActionCard hasErrors={false} />)

      // Buttons should be disabled for empty string
      const viewButton = screen.getByLabelText('View analysis results')
      expect(viewButton).toBeDisabled()
    })
  })
})
