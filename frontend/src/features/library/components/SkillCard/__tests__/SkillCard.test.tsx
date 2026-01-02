import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SkillCard } from '../SkillCard'

describe('SkillCard', () => {
  const defaultProps = {
    id: 'test-analysis-id',
    title: 'Test Analysis',
    description: 'This is a test analysis',
    difficulty: 'intermediate' as const,
    duration: 25,
    tags: ['article', 'react'],
    status: 'completed' as const,
    onSelect: vi.fn(),
  }

  it('renders analysis information correctly', () => {
    render(<SkillCard {...defaultProps} />)

    expect(screen.getByText('Test Analysis')).toBeInTheDocument()
    expect(screen.getByText('This is a test analysis')).toBeInTheDocument()
    expect(screen.getByText('intermediate')).toBeInTheDocument()
  })

  it('calls onSelect when card is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<SkillCard {...defaultProps} onSelect={onSelect} />)

    const card = screen.getByRole('button')
    await user.click(card)

    expect(onSelect).toHaveBeenCalledWith('test-analysis-id')
  })

  it('calls onSelect when Enter key is pressed', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<SkillCard {...defaultProps} onSelect={onSelect} />)

    const card = screen.getByRole('button')
    card.focus()
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith('test-analysis-id')
  })

  it('calls onSelect when Space key is pressed', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<SkillCard {...defaultProps} onSelect={onSelect} />)

    const card = screen.getByRole('button')
    card.focus()
    await user.keyboard(' ')

    expect(onSelect).toHaveBeenCalledWith('test-analysis-id')
  })

  describe('Error Display', () => {
    it('displays FailedStageDetails when status is failed', () => {
      render(
        <SkillCard
          {...defaultProps}
          status="failed"
          errorCode="EXTRACTION_FAILED"
          errorMessage="Failed to extract content"
          failedAtStage="extraction"
        />
      )

      expect(screen.getByText('Content Extraction Failed')).toBeInTheDocument()
      expect(screen.getByText('Failed at: Extraction')).toBeInTheDocument()
    })

    it('does not display error details when status is not failed', () => {
      render(<SkillCard {...defaultProps} status="completed" />)

      expect(screen.queryByText('Content Extraction Failed')).not.toBeInTheDocument()
    })

    it('passes error props to FailedStageDetails', () => {
      const onRetry = vi.fn()
      render(
        <SkillCard
          {...defaultProps}
          status="failed"
          errorCode="TECH_COMPARATOR_FAILED"
          errorMessage="Tech comparison failed"
          failedAtStage="tech_comparison"
          onRetry={onRetry}
        />
      )

      expect(screen.getByText('Technology Comparison Failed')).toBeInTheDocument()
      expect(screen.getByText('Failed at: Tech Comparison')).toBeInTheDocument()
    })

    it('does not show error details when error fields are missing', () => {
      render(<SkillCard {...defaultProps} status="failed" />)

      // Should still show "Failed" status badge, but no error details panel
      expect(screen.getByText('Failed')).toBeInTheDocument()
      expect(screen.queryByText('Content Extraction Failed')).not.toBeInTheDocument()
    })
  })

  describe('Delete functionality', () => {
    it('calls onDelete when delete button is clicked', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      render(<SkillCard {...defaultProps} onDelete={onDelete} />)

      const deleteButton = screen.getByLabelText('Delete analysis')
      await user.click(deleteButton)

      expect(onDelete).toHaveBeenCalledWith('test-analysis-id')
    })

    it('does not show delete button when onDelete is not provided', () => {
      render(<SkillCard {...defaultProps} />)

      expect(screen.queryByLabelText('Delete analysis')).not.toBeInTheDocument()
    })

    it('does not trigger onSelect when delete button is clicked', async () => {
      const user = userEvent.setup()
      const onSelect = vi.fn()
      const onDelete = vi.fn()
      render(<SkillCard {...defaultProps} onSelect={onSelect} onDelete={onDelete} />)

      const deleteButton = screen.getByLabelText('Delete analysis')
      await user.click(deleteButton)

      expect(onDelete).toHaveBeenCalled()
      expect(onSelect).not.toHaveBeenCalled()
    })
  })
})
