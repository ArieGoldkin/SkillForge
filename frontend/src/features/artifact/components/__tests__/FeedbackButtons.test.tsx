/**
 * Tests for FeedbackButtons component
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as useFeedbackModule from '../../hooks/useFeedback'
import { FeedbackButtons } from '../FeedbackButtons'

// Mock the useFeedback hook
const mockSubmitFeedback = vi.fn()
const mockFlagForReview = vi.fn()

vi.mock('../../hooks/useFeedback', () => ({
  useFeedback: vi.fn(),
}))

describe('FeedbackButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock implementation
    vi.mocked(useFeedbackModule.useFeedback).mockReturnValue({
      selectedFeedback: null,
      isSubmitting: false,
      submitFeedback: mockSubmitFeedback,
      flagForReview: mockFlagForReview,
    })
  })

  describe('Rendering', () => {
    it('renders thumbs up button', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsUpButton = screen.getByLabelText('This was helpful')
      expect(thumbsUpButton).toBeInTheDocument()
    })

    it('renders thumbs down button', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      expect(thumbsDownButton).toBeInTheDocument()
    })

    it('renders comment button', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const commentButton = screen.getByLabelText('Add comment')
      expect(commentButton).toBeInTheDocument()
    })

    it('displays "Was this helpful?" text', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(screen.getByText('Was this helpful?')).toBeInTheDocument()
    })
  })

  describe('Thumbs up interaction', () => {
    it('calls submitFeedback immediately when thumbs up is clicked', async () => {
      render(<FeedbackButtons artifactId="artifact-123" traceId="trace-456" />)

      const thumbsUpButton = screen.getByLabelText('This was helpful')
      await userEvent.click(thumbsUpButton)

      expect(mockSubmitFeedback).toHaveBeenCalledWith('thumbs_up')
      expect(mockSubmitFeedback).toHaveBeenCalledTimes(1)
    })

    it('does not show comment dialog for thumbs up', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsUpButton = screen.getByLabelText('This was helpful')
      await userEvent.click(thumbsUpButton)

      expect(screen.queryByText('Share your feedback')).not.toBeInTheDocument()
    })
  })

  describe('Thumbs down interaction', () => {
    it('shows comment dialog when thumbs down is clicked', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      await userEvent.click(thumbsDownButton)

      expect(screen.getByText('Share your feedback')).toBeInTheDocument()
    })

    it('does not call submitFeedback immediately when thumbs down is clicked', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      await userEvent.click(thumbsDownButton)

      expect(mockSubmitFeedback).not.toHaveBeenCalled()
    })
  })

  describe('Comment dialog interaction', () => {
    it('shows comment dialog when comment button is clicked', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const commentButton = screen.getByLabelText('Add comment')
      await userEvent.click(commentButton)

      expect(screen.getByText('Share your feedback')).toBeInTheDocument()
    })

    it('submits feedback with comment when dialog is submitted', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      // Open dialog via thumbs down
      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      await userEvent.click(thumbsDownButton)

      // Enter comment
      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Missing code examples')

      // Submit
      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      expect(mockSubmitFeedback).toHaveBeenCalledWith('thumbs_down', 'Missing code examples')
    })

    it('submits feedback without comment when Skip is clicked', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      // Open dialog via thumbs down
      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      await userEvent.click(thumbsDownButton)

      // Click Skip
      const skipButton = screen.getByText('Skip')
      await userEvent.click(skipButton)

      expect(mockSubmitFeedback).toHaveBeenCalledWith('thumbs_down')
    })

    it('closes dialog after submission', async () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      // Open dialog
      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      await userEvent.click(thumbsDownButton)

      // Submit
      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      // Dialog should be closed
      expect(screen.queryByText('Share your feedback')).not.toBeInTheDocument()
    })
  })

  describe('Button states', () => {
    it('highlights thumbs up button when selected', () => {
      vi.mocked(useFeedbackModule.useFeedback).mockReturnValue({
        selectedFeedback: 'thumbs_up',
        isSubmitting: false,
        submitFeedback: mockSubmitFeedback,
        flagForReview: mockFlagForReview,
      })

      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsUpButton = screen.getByLabelText('This was helpful')
      expect(thumbsUpButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('highlights thumbs down button when selected', () => {
      vi.mocked(useFeedbackModule.useFeedback).mockReturnValue({
        selectedFeedback: 'thumbs_down',
        isSubmitting: false,
        submitFeedback: mockSubmitFeedback,
        flagForReview: mockFlagForReview,
      })

      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsDownButton = screen.getByLabelText('This was not helpful')
      expect(thumbsDownButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('disables all buttons while submitting', () => {
      vi.mocked(useFeedbackModule.useFeedback).mockReturnValue({
        selectedFeedback: null,
        isSubmitting: true,
        submitFeedback: mockSubmitFeedback,
        flagForReview: mockFlagForReview,
      })

      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(screen.getByLabelText('This was helpful')).toBeDisabled()
      expect(screen.getByLabelText('This was not helpful')).toBeDisabled()
      expect(screen.getByLabelText('Add comment')).toBeDisabled()
    })

    it('enables all buttons when not submitting', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(screen.getByLabelText('This was helpful')).not.toBeDisabled()
      expect(screen.getByLabelText('This was not helpful')).not.toBeDisabled()
      expect(screen.getByLabelText('Add comment')).not.toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has accessible labels on all buttons', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(screen.getByLabelText('This was helpful')).toBeInTheDocument()
      expect(screen.getByLabelText('This was not helpful')).toBeInTheDocument()
      expect(screen.getByLabelText('Add comment')).toBeInTheDocument()
    })

    it('has screen reader text for icon buttons', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(screen.getByText('Thumbs up')).toHaveClass('sr-only')
      expect(screen.getByText('Thumbs down')).toHaveClass('sr-only')
      expect(screen.getByText('Add comment')).toHaveClass('sr-only')
    })

    it('sets aria-pressed on feedback buttons', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      const thumbsUpButton = screen.getByLabelText('This was helpful')
      const thumbsDownButton = screen.getByLabelText('This was not helpful')

      expect(thumbsUpButton).toHaveAttribute('aria-pressed', 'false')
      expect(thumbsDownButton).toHaveAttribute('aria-pressed', 'false')
    })
  })

  describe('Props handling', () => {
    it('passes artifactId to useFeedback hook', () => {
      render(<FeedbackButtons artifactId="artifact-123" />)

      expect(useFeedbackModule.useFeedback).toHaveBeenCalledWith({
        artifactId: 'artifact-123',
        traceId: undefined,
      })
    })

    it('passes traceId to useFeedback hook when provided', () => {
      render(<FeedbackButtons artifactId="artifact-123" traceId="trace-456" />)

      expect(useFeedbackModule.useFeedback).toHaveBeenCalledWith({
        artifactId: 'artifact-123',
        traceId: 'trace-456',
      })
    })

    it('applies custom className', () => {
      const { container } = render(
        <FeedbackButtons artifactId="artifact-123" className="custom-class" />
      )

      expect(container.querySelector('.custom-class')).toBeInTheDocument()
    })
  })
})
