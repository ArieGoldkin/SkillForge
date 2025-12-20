import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CommonAnalysisLayout } from '../CommonAnalysisLayout'

vi.mock('../../steps/AnalysisHeader', () => ({
  AnalysisHeader: ({ title, url }: { title: string; url: string }) => (
    <header data-testid="analysis-header">
      <h1>{title}</h1>
      <p>{url}</p>
    </header>
  ),
}))

vi.mock('../../TimeoutWarningBanner', () => ({
  TimeoutWarningBanner: ({
    showTimeoutWarning,
    onDismiss,
  }: {
    showTimeoutWarning: boolean
    onDismiss: () => void
  }) =>
    showTimeoutWarning ? (
      <div data-testid="timeout-warning-banner">
        <button type="button" onClick={onDismiss} data-testid="dismiss-timeout">
          Dismiss
        </button>
      </div>
    ) : null,
}))

describe('CommonAnalysisLayout', () => {
  // Clean up after each test to ensure isolation
  afterEach(() => {
    vi.clearAllMocks()
  })
  const defaultProps = {
    analysisMetadata: {
      title: 'Test Analysis',
      url: 'https://test.com',
      contentType: 'article' as const,
      wordCount: 1000,
    },
    analysisId: 'test-id',
  }

  it('renders children correctly', () => {
    render(
      <CommonAnalysisLayout {...defaultProps}>
        <div data-testid="test-child">Test Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.getByTestId('test-child')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('renders AnalysisHeader with correct props', () => {
    render(
      <CommonAnalysisLayout {...defaultProps}>
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    // Mock provides data-testid="analysis-header"
    expect(screen.getByTestId('analysis-header')).toBeInTheDocument()
    expect(screen.getByText('Test Analysis')).toBeInTheDocument()
    expect(screen.getByText('https://test.com')).toBeInTheDocument()
  })

  it('uses fallback values when metadata is missing', () => {
    render(
      <CommonAnalysisLayout analysisId="fallback-id">
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.getByText('Content Analysis')).toBeInTheDocument()
    expect(screen.getByText('Analysis ID: fallback-id')).toBeInTheDocument()
  })

  it('renders timeout warning banner when showTimeoutWarning is true and onTimeoutWarningDismiss is provided', () => {
    const mockOnDismiss = vi.fn()

    render(
      <CommonAnalysisLayout
        {...defaultProps}
        showTimeoutWarning={true}
        onTimeoutWarningDismiss={mockOnDismiss}
      >
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.getByTestId('timeout-warning-banner')).toBeInTheDocument()
    expect(screen.getByTestId('dismiss-timeout')).toBeInTheDocument()
  })

  it('does not render timeout warning when showTimeoutWarning is false', () => {
    render(
      <CommonAnalysisLayout
        {...defaultProps}
        showTimeoutWarning={false}
        onTimeoutWarningDismiss={vi.fn()}
      >
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.queryByTestId('timeout-warning-banner')).not.toBeInTheDocument()
  })

  it('does not render timeout warning when onTimeoutWarningDismiss is not provided', () => {
    render(
      <CommonAnalysisLayout {...defaultProps} showTimeoutWarning={true}>
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.queryByTestId('timeout-warning-banner')).not.toBeInTheDocument()
  })

  it('handles timeout warning dismissal', () => {
    const mockOnDismiss = vi.fn()

    render(
      <CommonAnalysisLayout
        {...defaultProps}
        showTimeoutWarning={true}
        onTimeoutWarningDismiss={mockOnDismiss}
      >
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    const dismissButton = screen.getByTestId('dismiss-timeout')
    fireEvent.click(dismissButton)

    expect(mockOnDismiss).toHaveBeenCalledTimes(1)
  })

  it('renders progress content when provided', () => {
    render(
      <CommonAnalysisLayout
        {...defaultProps}
        progressContent={<div data-testid="progress-content">Progress Here</div>}
      >
        <div>Main Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.getByTestId('progress-content')).toBeInTheDocument()
    expect(screen.getByText('Progress Here')).toBeInTheDocument()
  })

  it('does not render progress content when not provided', () => {
    render(
      <CommonAnalysisLayout {...defaultProps}>
        <div>Main Content</div>
      </CommonAnalysisLayout>
    )

    expect(screen.queryByTestId('progress-content')).not.toBeInTheDocument()
  })

  it('applies correct CSS classes', () => {
    const { container } = render(
      <CommonAnalysisLayout {...defaultProps}>
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    const layoutDiv = container.firstChild as HTMLElement
    expect(layoutDiv).toHaveClass('container', 'mx-auto', 'px-4', 'py-8', 'max-w-7xl')
  })

  it('renders all sections in correct order', () => {
    const mockOnDismiss = vi.fn()

    render(
      <CommonAnalysisLayout
        {...defaultProps}
        showTimeoutWarning={true}
        onTimeoutWarningDismiss={mockOnDismiss}
        progressContent={<div data-testid="progress">Progress</div>}
      >
        <div data-testid="children">Children</div>
      </CommonAnalysisLayout>
    )

    // Check that all sections are present and in correct order
    const layoutDiv = screen.getByTestId('common-analysis-layout')
    const headerSection = layoutDiv.children[0] as HTMLElement
    const timeoutSection = layoutDiv.children[1] as HTMLElement
    const childrenSection = layoutDiv.children[2] as HTMLElement
    const progressSection = layoutDiv.children[3] as HTMLElement

    // Header section IS the analysis header (mocked)
    expect(headerSection).toHaveAttribute('data-testid', 'analysis-header')
    // Timeout warning is directly rendered
    expect(timeoutSection).toHaveAttribute('data-testid', 'timeout-warning-banner')
    // Children are directly rendered
    expect(childrenSection).toHaveAttribute('data-testid', 'children')
    // Progress is directly rendered
    expect(progressSection).toHaveAttribute('data-testid', 'progress')
  })

  it('handles empty metadata gracefully', () => {
    render(
      <CommonAnalysisLayout>
        <div>Content</div>
      </CommonAnalysisLayout>
    )

    // Should render default title and not crash
    expect(screen.getByText('Content Analysis')).toBeInTheDocument()
    // Should not have any undefined or empty text issues
    expect(screen.queryByText('undefined')).not.toBeInTheDocument()
  })
})
