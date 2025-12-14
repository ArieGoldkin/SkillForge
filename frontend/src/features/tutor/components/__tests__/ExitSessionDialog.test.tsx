import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ExitSessionDialog } from '../ExitSessionDialog'

describe('ExitSessionDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onConfirm: vi.fn(),
    isPending: false,
  }

  it('renders dialog with title and description when open', () => {
    render(<ExitSessionDialog {...defaultProps} />)

    expect(screen.getByText('Exit Tutoring Session?')).toBeInTheDocument()
    expect(
      screen.getByText(/Are you sure you want to end this tutoring session/i)
    ).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(<ExitSessionDialog {...defaultProps} open={false} />)

    expect(screen.queryByText('Exit Tutoring Session?')).not.toBeInTheDocument()
  })

  it('calls onConfirm when End Session button is clicked', async () => {
    const onConfirm = vi.fn()
    render(<ExitSessionDialog {...defaultProps} onConfirm={onConfirm} />)

    await userEvent.click(screen.getByTestId('confirm-exit-button'))

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onOpenChange with false when Cancel button is clicked', async () => {
    const onOpenChange = vi.fn()
    render(<ExitSessionDialog {...defaultProps} onOpenChange={onOpenChange} />)

    await userEvent.click(screen.getByTestId('cancel-exit-button'))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('disables End Session button when isPending is true', () => {
    render(<ExitSessionDialog {...defaultProps} isPending={true} />)

    const confirmButton = screen.getByTestId('confirm-exit-button')
    expect(confirmButton).toBeDisabled()
    expect(confirmButton).toHaveTextContent('Ending...')
  })

  it('shows "End Session" text when not pending', () => {
    render(<ExitSessionDialog {...defaultProps} isPending={false} />)

    expect(screen.getByTestId('confirm-exit-button')).toHaveTextContent('End Session')
  })
})
