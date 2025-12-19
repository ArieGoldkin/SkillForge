import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TimeoutWarningBanner } from '../TimeoutWarningBanner'

describe('TimeoutWarningBanner', () => {
  const defaultProps = {
    showTimeoutWarning: true,
    onDismiss: vi.fn(),
  }

  it('renders when showTimeoutWarning is true', () => {
    render(<TimeoutWarningBanner {...defaultProps} />)

    expect(screen.getByText(/This analysis is taking longer than expected/)).toBeInTheDocument()
    expect(screen.getByText(/Please continue waiting/)).toBeInTheDocument()
  })

  it('does not render when showTimeoutWarning is false', () => {
    render(<TimeoutWarningBanner {...defaultProps} showTimeoutWarning={false} />)

    expect(screen.queryByText(/taking longer than expected/)).not.toBeInTheDocument()
  })

  it('calls onDismiss when dismiss button is clicked', () => {
    render(<TimeoutWarningBanner {...defaultProps} />)

    const dismissButton = screen.getByRole('button', { name: /dismiss timeout warning/i })
    fireEvent.click(dismissButton)

    expect(defaultProps.onDismiss).toHaveBeenCalledTimes(1)
  })

  it('has correct accessibility attributes', () => {
    render(<TimeoutWarningBanner {...defaultProps} />)

    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(alert).toHaveClass('border-orange-200', 'bg-orange-50', 'text-orange-800')
  })

  it('dismiss button has correct accessibility attributes', () => {
    render(<TimeoutWarningBanner {...defaultProps} />)

    const dismissButton = screen.getByRole('button', { name: /dismiss timeout warning/i })
    expect(dismissButton).toHaveAttribute('aria-label', 'Dismiss timeout warning')
  })
})
