import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { FailedStageDetails } from '../FailedStageDetails'

describe('FailedStageDetails', () => {
  const defaultProps = {
    analysisId: 'test-analysis-id',
    errorCode: 'EXTRACTION_FAILED',
    errorMessage: 'Unable to extract content from URL',
    failedAtStage: 'extraction',
    onRetry: vi.fn(),
  }

  it('renders error information when collapsed', () => {
    render(<FailedStageDetails {...defaultProps} />)

    expect(screen.getByText('Content Extraction Failed')).toBeInTheDocument()
    expect(screen.getByText('Failed at: Extraction')).toBeInTheDocument()
  })

  it('expands to show error details when clicked', async () => {
    const user = userEvent.setup()
    render(<FailedStageDetails {...defaultProps} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    expect(screen.getByText('Why this failed:')).toBeInTheDocument()
    expect(screen.getByText('Unable to extract content from URL')).toBeInTheDocument()
    expect(screen.getByText('How to fix:')).toBeInTheDocument()
    expect(screen.getByText(/The page may not be accessible/)).toBeInTheDocument()
  })

  it('shows retry button when error is retryable', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<FailedStageDetails {...defaultProps} onRetry={onRetry} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeInTheDocument()
    expect(retryButton).toHaveTextContent('Retry Extraction')
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<FailedStageDetails {...defaultProps} onRetry={onRetry} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    const retryButton = screen.getByRole('button', { name: /retry extraction/i })
    await user.click(retryButton)

    expect(onRetry).toHaveBeenCalledWith('test-analysis-id', 'extraction')
  })

  it('does not show retry button when error is not retryable', async () => {
    const user = userEvent.setup()
    // ERROR_PAGE is not retryable
    render(<FailedStageDetails {...defaultProps} errorCode="ERROR_PAGE" onRetry={vi.fn()} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    const retryButtons = screen.getAllByRole('button')
    // Should only have the collapse trigger, no retry button
    expect(retryButtons).toHaveLength(1)
  })

  it('uses error message from backend when available', async () => {
    const user = userEvent.setup()
    render(<FailedStageDetails {...defaultProps} errorMessage="Custom backend error message" />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    expect(screen.getByText('Custom backend error message')).toBeInTheDocument()
  })

  it('falls back to explanation reason when error message is not available', async () => {
    const user = userEvent.setup()
    render(<FailedStageDetails {...defaultProps} errorMessage={null} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    // Should show the reason from error explanation
    expect(screen.getByText(/Unable to extract content from the URL/)).toBeInTheDocument()
  })

  it('formats stage names correctly', () => {
    render(<FailedStageDetails {...defaultProps} failedAtStage="tech_comparison" />)

    expect(screen.getByText('Failed at: Tech Comparison')).toBeInTheDocument()
  })

  it('handles missing stage name gracefully', () => {
    render(<FailedStageDetails {...defaultProps} failedAtStage={null} />)

    expect(screen.getByText('Content Extraction Failed')).toBeInTheDocument()
    expect(screen.queryByText('Failed at:')).not.toBeInTheDocument()
  })

  it('can be expanded by default with defaultExpanded prop', () => {
    render(<FailedStageDetails {...defaultProps} defaultExpanded={true} />)

    expect(screen.getByText('Why this failed:')).toBeInTheDocument()
    expect(screen.getByText('How to fix:')).toBeInTheDocument()
  })

  it('handles unknown error codes with fallback', async () => {
    const user = userEvent.setup()
    render(<FailedStageDetails {...defaultProps} errorCode="UNKNOWN_ERROR_CODE" />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    // Should show fallback title and reason
    expect(screen.getByText('Unknown Error Code')).toBeInTheDocument()
  })
})
