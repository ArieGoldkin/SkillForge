import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { LoadingState } from '@types/loading'

import { LoadingStateDisplay } from '../LoadingStateDisplay'

describe('LoadingStateDisplay', () => {
  const renderComponent = (loadingState: LoadingState) => {
    return render(<LoadingStateDisplay loadingState={loadingState} />)
  }

  it('displays waiting for events state', () => {
    renderComponent({ type: 'waiting_for_events', connectedAt: Date.now() })

    expect(screen.getByText('Preparing analysis...')).toBeInTheDocument()
    expect(screen.getByText('Setting up your content analysis')).toBeInTheDocument()
  })

  it('displays extracting state with word count', () => {
    renderComponent({
      type: 'extracting',
      stage: 'extraction',
      status: 'running',
      wordCount: 1234,
    })

    expect(screen.getByText('Extracting content...')).toBeInTheDocument()
    expect(screen.getByText('Processing 1,234 words')).toBeInTheDocument()
  })

  it('displays extracting state without word count', () => {
    renderComponent({
      type: 'extracting',
      stage: 'extraction',
      status: 'running',
    })

    expect(screen.getByText('Extracting content...')).toBeInTheDocument()
    expect(screen.getByText('Reading and analyzing your content')).toBeInTheDocument()
  })

  it('displays analyzing state with progress', () => {
    renderComponent({
      type: 'analyzing',
      stage: 'tech_comparison',
      status: 'running',
      progress: 75,
    })

    expect(screen.getByText('Analyzing content...')).toBeInTheDocument()
    expect(screen.getByText('Running AI analysis (75%)')).toBeInTheDocument()
  })

  it('displays generating state', () => {
    renderComponent({
      type: 'generating',
      stage: 'artifact_generation',
      status: 'running',
    })

    expect(screen.getByText('Generating report...')).toBeInTheDocument()
    expect(screen.getByText('Compiling your analysis results')).toBeInTheDocument()
  })

  it('displays complete state', () => {
    renderComponent({
      type: 'complete',
      artifactId: 'test-artifact-id',
    })

    expect(screen.getByText('Analysis complete')).toBeInTheDocument()
    expect(screen.getByText('Your results are ready to view')).toBeInTheDocument()
  })

  it('displays error state', () => {
    renderComponent({
      type: 'error',
      error: 'Something went wrong',
    })

    expect(screen.getByText('Analysis failed')).toBeInTheDocument()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('displays connecting state', () => {
    renderComponent({ type: 'connecting', startTime: Date.now() })

    expect(screen.getByText('Connecting...')).toBeInTheDocument()
    expect(screen.getByText('Establishing connection')).toBeInTheDocument()
  })
})
