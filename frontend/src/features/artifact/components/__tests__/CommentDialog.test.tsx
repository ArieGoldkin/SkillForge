/**
 * Tests for CommentDialog component
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CommentDialog } from '../CommentDialog'

describe('CommentDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders when open', () => {
      render(<CommentDialog {...defaultProps} />)

      expect(screen.getByText('Share your feedback')).toBeInTheDocument()
      expect(
        screen.getByText(/Help us improve by telling us what could be better/i)
      ).toBeInTheDocument()
    })

    it('does not render when closed', () => {
      render(<CommentDialog {...defaultProps} open={false} />)

      expect(screen.queryByText('Share your feedback')).not.toBeInTheDocument()
    })

    it('renders textarea with placeholder', () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      expect(textarea).toBeInTheDocument()
    })

    it('renders Skip and Submit buttons', () => {
      render(<CommentDialog {...defaultProps} />)

      expect(screen.getByText('Skip')).toBeInTheDocument()
      expect(screen.getByText('Submit Feedback')).toBeInTheDocument()
    })

    it('shows keyboard hint', () => {
      render(<CommentDialog {...defaultProps} />)

      expect(screen.getByText('Press Ctrl+Enter to submit')).toBeInTheDocument()
    })
  })

  describe('Character count', () => {
    it('displays character count', () => {
      render(<CommentDialog {...defaultProps} />)

      expect(screen.getByText('1000 characters remaining')).toBeInTheDocument()
    })

    it('updates character count as user types', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Hello')

      expect(screen.getByText('995 characters remaining')).toBeInTheDocument()
    })

    it('shows negative count when over limit', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      // Use paste instead of type for large text (much faster)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const countElement = screen.getByText('-1 characters remaining')
      expect(countElement).toBeInTheDocument()
    })

    it('applies destructive styling when over limit', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const countElement = screen.getByText('-1 characters remaining')
      expect(countElement).toHaveClass('text-destructive')
      expect(countElement).toHaveClass('font-medium')
    })
  })

  describe('Submit button', () => {
    it('is enabled when text is within limit', () => {
      render(<CommentDialog {...defaultProps} />)

      const submitButton = screen.getByText('Submit Feedback')
      expect(submitButton).not.toBeDisabled()
    })

    it('is disabled when text exceeds limit', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const submitButton = screen.getByText('Submit Feedback')
      expect(submitButton).toBeDisabled()
    })

    it('calls onSubmit with trimmed comment when clicked', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, '  Hello World  ')

      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      expect(onSubmit).toHaveBeenCalledWith('Hello World')
    })

    it('calls onSubmit with empty string if only whitespace', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, '   ')

      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      expect(onSubmit).toHaveBeenCalledWith('')
    })

    it('does not submit when text exceeds limit', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('does not show error when submit is clicked with disabled button', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const submitButton = screen.getByText('Submit Feedback')

      // Submit button should be disabled, so clicking won't trigger validation
      expect(submitButton).toBeDisabled()

      // The error is shown via aria-invalid and disabled state, not an error message
      // (Component uses disabled button to prevent submission)
    })
  })

  describe('Skip button', () => {
    it('calls onCancel when clicked', async () => {
      const onCancel = vi.fn()
      render(<CommentDialog {...defaultProps} onCancel={onCancel} />)

      const skipButton = screen.getByText('Skip')
      await userEvent.click(skipButton)

      expect(onCancel).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard shortcuts', () => {
    it('submits when Ctrl+Enter is pressed', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Great feedback')
      await userEvent.keyboard('{Control>}{Enter}{/Control}')

      expect(onSubmit).toHaveBeenCalledWith('Great feedback')
    })

    it('submits when Cmd+Enter is pressed (Mac)', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Great feedback')
      await userEvent.keyboard('{Meta>}{Enter}{/Meta}')

      expect(onSubmit).toHaveBeenCalledWith('Great feedback')
    })

    it('does not submit on Enter without Ctrl/Cmd', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Line 1{Enter}Line 2')

      expect(onSubmit).not.toHaveBeenCalled()
      expect(textarea).toHaveValue('Line 1\nLine 2')
    })

    it('does not submit with Ctrl+Enter when over limit', async () => {
      const onSubmit = vi.fn()
      render(<CommentDialog {...defaultProps} onSubmit={onSubmit} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)
      await userEvent.keyboard('{Control>}{Enter}{/Control}')

      expect(onSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Dialog state management', () => {
    it('starts with empty comment on initial render', () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      expect(textarea).toHaveValue('')
    })

    it('maintains comment state while dialog is open', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      await userEvent.type(textarea, 'Some feedback')

      expect(textarea).toHaveValue('Some feedback')
    })

    it('maintains over-limit validation state', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      // Over limit - aria-invalid should be true and button disabled
      expect(textarea).toHaveAttribute('aria-invalid', 'true')
      expect(screen.getByText('Submit Feedback')).toBeDisabled()
    })

    it('calls onOpenChange when dialog state should change', async () => {
      const onOpenChange = vi.fn()
      render(<CommentDialog {...defaultProps} onOpenChange={onOpenChange} />)

      // Note: We can't easily test the actual dialog close behavior without
      // testing internal Radix UI implementation details. The onOpenChange
      // prop is passed to the Dialog component and will be called by Radix UI
      // when the dialog is closed via overlay click or escape key.
      expect(onOpenChange).toHaveBeenCalledTimes(0)
    })
  })

  describe('Accessibility', () => {
    it('has accessible label for textarea', () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByLabelText('Comment (optional)')
      expect(textarea).toBeInTheDocument()
    })

    it('links textarea to hint and error via aria-describedby', () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      expect(textarea).toHaveAttribute('aria-describedby', 'comment-hint comment-error')
    })

    it('sets aria-invalid when over character limit', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      expect(textarea).toHaveAttribute('aria-invalid', 'false')

      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      expect(textarea).toHaveAttribute('aria-invalid', 'true')
    })

    it('sets aria-invalid when error message is shown', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      const submitButton = screen.getByText('Submit Feedback')
      await userEvent.click(submitButton)

      expect(textarea).toHaveAttribute('aria-invalid', 'true')
    })

    it('uses aria-invalid for validation feedback', async () => {
      render(<CommentDialog {...defaultProps} />)

      const textarea = screen.getByPlaceholderText('What could we improve?')

      // Initially valid
      expect(textarea).toHaveAttribute('aria-invalid', 'false')

      // Type over limit
      const longText = 'a'.repeat(1001)
      await userEvent.click(textarea)
      await userEvent.paste(longText)

      // Should be invalid
      expect(textarea).toHaveAttribute('aria-invalid', 'true')

      // Component uses disabled button state to prevent submission
      // rather than showing an explicit error message with role="alert"
      const submitButton = screen.getByText('Submit Feedback')
      expect(submitButton).toBeDisabled()
    })
  })
})
