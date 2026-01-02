import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AnalysisProgressCardErrorSummary } from '../AnalysisProgressCardErrorSummary'

describe('AnalysisProgressCardErrorSummary', () => {
  it('displays failure count and primary error reason', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={9}
        failedStageErrorCodes={['EXTRACTION_FAILED']}
      />
    )

    expect(screen.getByText(/Analysis completed with 9 failures/)).toBeInTheDocument()
    expect(screen.getByText(/Unable to extract content from the URL/)).toBeInTheDocument()
  })

  it('groups errors by critical vs non-critical', async () => {
    const user = userEvent.setup()
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={5}
        failedStageErrorCodes={[
          'EXTRACTION_FAILED',
          'ANALYSIS_FAILED',
          'TECH_COMPARATOR_FAILED',
          'SECURITY_AUDITOR_FAILED',
          'PERFORMANCE_ANALYST_FAILED',
        ]}
      />
    )

    // Expand error details
    const expandButton = screen.getByRole('button', { name: /show error details/i })
    await user.click(expandButton)

    // Should show critical errors section
    expect(screen.getByText('Critical Errors:')).toBeInTheDocument()
    expect(screen.getByText('Non-Critical Errors:')).toBeInTheDocument()

    // Should show critical error badges
    expect(screen.getByText('Content Extraction Failed')).toBeInTheDocument()
    expect(screen.getByText('Analysis Failed')).toBeInTheDocument()

    // Should show non-critical error badges
    expect(screen.getByText('Technology Comparison Failed')).toBeInTheDocument()
    expect(screen.getByText('Security Audit Failed')).toBeInTheDocument()
  })

  it('shows actionable guidance from primary error', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={3}
        failedStageErrorCodes={['TECH_COMPARATOR_FAILED']}
      />
    )

    expect(screen.getByText('What you can do:')).toBeInTheDocument()
    expect(screen.getByText(/This stage requires technology comparisons/)).toBeInTheDocument()
  })

  it('displays critical error count when present', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={5}
        failedStageErrorCodes={['EXTRACTION_FAILED', 'ANALYSIS_FAILED', 'TECH_COMPARATOR_FAILED']}
      />
    )

    expect(screen.getByText(/2 critical errors may affect results/)).toBeInTheDocument()
  })

  it('does not show critical error count when no critical errors', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={3}
        failedStageErrorCodes={[
          'TECH_COMPARATOR_FAILED',
          'SECURITY_AUDITOR_FAILED',
          'PERFORMANCE_ANALYST_FAILED',
        ]}
      />
    )

    expect(screen.queryByText(/critical errors may affect results/)).not.toBeInTheDocument()
  })

  it('expands/collapses error details on click', async () => {
    const user = userEvent.setup()
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={2}
        failedStageErrorCodes={['EXTRACTION_FAILED', 'ANALYSIS_FAILED']}
      />
    )

    // Initially collapsed
    expect(screen.queryByText('Critical Errors:')).not.toBeInTheDocument()

    // Expand
    const expandButton = screen.getByRole('button', { name: /show error details/i })
    await user.click(expandButton)

    expect(screen.getByText('Critical Errors:')).toBeInTheDocument()

    // Collapse
    const collapseButton = screen.getByRole('button', { name: /hide error details/i })
    await user.click(collapseButton)

    expect(screen.queryByText('Critical Errors:')).not.toBeInTheDocument()
  })

  it('calls onViewDetails when view details button is clicked', async () => {
    const user = userEvent.setup()
    const onViewDetails = vi.fn()
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={2}
        failedStageErrorCodes={['EXTRACTION_FAILED']}
        onViewDetails={onViewDetails}
      />
    )

    const viewDetailsButton = screen.getByRole('button', {
      name: /view detailed error information/i,
    })
    await user.click(viewDetailsButton)

    expect(onViewDetails).toHaveBeenCalledTimes(1)
  })

  it('does not show view details button when onViewDetails is not provided', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={2}
        failedStageErrorCodes={['EXTRACTION_FAILED']}
      />
    )

    expect(
      screen.queryByRole('button', { name: /view detailed error information/i })
    ).not.toBeInTheDocument()
  })

  it('handles empty error codes gracefully', () => {
    render(<AnalysisProgressCardErrorSummary failedStagesCount={0} failedStageErrorCodes={[]} />)

    expect(screen.getByText(/Analysis completed with 0 failures/)).toBeInTheDocument()
  })

  it('displays correct error count in expand button', () => {
    render(
      <AnalysisProgressCardErrorSummary
        failedStagesCount={5}
        failedStageErrorCodes={['EXTRACTION_FAILED', 'ANALYSIS_FAILED', 'TECH_COMPARATOR_FAILED']}
      />
    )

    expect(screen.getByText(/Show error details \(3 errors\)/)).toBeInTheDocument()
  })
})
