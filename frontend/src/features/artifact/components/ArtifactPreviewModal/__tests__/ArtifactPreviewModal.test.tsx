/**
 * Tests for ArtifactPreviewModal component
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ArtifactPreviewModal } from '../'

// Mock ModalContent to avoid MarkdownPreview CSS import issues
vi.mock('../internal', () => ({
  ModalContent: ({
    content,
    isLoading,
    error,
  }: {
    content: string | null
    isLoading: boolean
    error: Error | null
  }) => {
    if (isLoading) {
      return <div>Loading preview...</div>
    }
    if (error) {
      return (
        <div>
          <p>Failed to load preview</p>
          <p>{error.message}</p>
        </div>
      )
    }
    if (content) {
      return <div data-testid="markdown-preview">{content}</div>
    }
    return null
  },
}))

describe('ArtifactPreviewModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    content: null,
    isLoading: false,
    error: null,
    onDownload: vi.fn(),
  }

  describe('Rendering', () => {
    it('renders modal title when open', () => {
      render(<ArtifactPreviewModal {...defaultProps} />)

      expect(screen.getByText('Implementation Guide Preview')).toBeInTheDocument()
    })

    it('does not render when closed', () => {
      render(<ArtifactPreviewModal {...defaultProps} isOpen={false} />)

      expect(screen.queryByText('Implementation Guide Preview')).not.toBeInTheDocument()
    })

    it('renders source URL when provided', () => {
      render(<ArtifactPreviewModal {...defaultProps} sourceUrl="https://example.com/article" />)

      expect(screen.getByText('https://example.com/article')).toBeInTheDocument()
    })

    it('does not render source URL when not provided', () => {
      render(<ArtifactPreviewModal {...defaultProps} />)

      expect(screen.queryByText('https://example.com')).not.toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(<ArtifactPreviewModal {...defaultProps} isLoading={true} />)

      expect(screen.getByText('Loading preview...')).toBeInTheDocument()
    })

    it('disables download button when loading', () => {
      render(<ArtifactPreviewModal {...defaultProps} isLoading={true} />)

      const downloadButton = screen.getByRole('button', { name: /download guide/i })
      expect(downloadButton).toBeDisabled()
    })
  })

  describe('Error State', () => {
    it('shows error message when error is provided', () => {
      const error = new Error('Failed to fetch artifact')
      render(<ArtifactPreviewModal {...defaultProps} error={error} />)

      expect(screen.getByText('Failed to load preview')).toBeInTheDocument()
      expect(screen.getByText('Failed to fetch artifact')).toBeInTheDocument()
    })
  })

  describe('Content Display', () => {
    it('renders markdown content when provided', () => {
      const content = '# Test Guide\n\nThis is test content.'
      render(<ArtifactPreviewModal {...defaultProps} content={content} />)

      const preview = screen.getByTestId('markdown-preview')
      expect(preview).toBeInTheDocument()
      expect(preview.textContent).toContain('Test Guide')
    })

    it('enables download button when content is available', () => {
      render(<ArtifactPreviewModal {...defaultProps} content="# Content" />)

      const downloadButton = screen.getByRole('button', { name: /download guide/i })
      expect(downloadButton).not.toBeDisabled()
    })
  })

  describe('Actions', () => {
    it('calls onClose when Close button is clicked', () => {
      const onClose = vi.fn()
      render(<ArtifactPreviewModal {...defaultProps} onClose={onClose} />)

      // Get the footer Close button (not the X button which also has 'Close' in sr-only)
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      // Footer close button is before the X button in DOM order
      fireEvent.click(closeButtons[0])

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onDownload and onClose when Download button is clicked', () => {
      const onClose = vi.fn()
      const onDownload = vi.fn()
      render(
        <ArtifactPreviewModal
          {...defaultProps}
          content="# Content"
          onClose={onClose}
          onDownload={onDownload}
        />
      )

      fireEvent.click(screen.getByRole('button', { name: /download guide/i }))

      expect(onDownload).toHaveBeenCalledTimes(1)
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('disables download button when content is null', () => {
      render(<ArtifactPreviewModal {...defaultProps} content={null} />)

      const downloadButton = screen.getByRole('button', { name: /download guide/i })
      expect(downloadButton).toBeDisabled()
    })
  })

  describe('Footer Buttons', () => {
    it('renders Close and Download buttons', () => {
      render(<ArtifactPreviewModal {...defaultProps} content="# Content" />)

      // There are two close buttons - footer and X button
      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      expect(closeButtons.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByRole('button', { name: /download guide/i })).toBeInTheDocument()
    })
  })
})
