import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { TopicSelectModal } from '../'
import type { TutoringTopic } from '../types'

const mockTopics: TutoringTopic[] = [
  { id: 'topic-1', name: 'React Basics', description: 'Learn React fundamentals' },
  { id: 'topic-2', name: 'TypeScript', description: 'Type safety in JS' },
  { id: 'topic-3', name: 'Testing', description: 'Unit and integration tests' },
]

describe('TopicSelectModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSelect: vi.fn(),
    topics: mockTopics,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders modal with title when open', () => {
      render(<TopicSelectModal {...defaultProps} />)
      expect(screen.getByText('Start Tutoring Session')).toBeInTheDocument()
    })

    it('renders all topics', () => {
      render(<TopicSelectModal {...defaultProps} />)
      expect(screen.getByText('React Basics')).toBeInTheDocument()
      expect(screen.getByText('TypeScript')).toBeInTheDocument()
      expect(screen.getByText('Testing')).toBeInTheDocument()
    })

    it('shows analysis title in description when provided', () => {
      render(<TopicSelectModal {...defaultProps} analysisTitle="My Analysis" />)
      expect(screen.getByText(/Select a topic from "My Analysis"/)).toBeInTheDocument()
    })

    it('shows loading state when isLoading is true', () => {
      render(<TopicSelectModal {...defaultProps} isLoading />)
      expect(screen.queryByText('React Basics')).not.toBeInTheDocument()
    })

    it('shows empty state when no topics', () => {
      render(<TopicSelectModal {...defaultProps} topics={[]} />)
      expect(screen.getByText('No topics available for this analysis.')).toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('enables Start Learning button when topic is selected', async () => {
      render(<TopicSelectModal {...defaultProps} />)
      const startButton = screen.getByRole('button', { name: /Start Learning/ })
      expect(startButton).toBeDisabled()

      fireEvent.click(screen.getByText('React Basics'))

      await waitFor(() => {
        expect(startButton).not.toBeDisabled()
      })
    })

    it('calls onSelect with topic id when Start Learning clicked', async () => {
      render(<TopicSelectModal {...defaultProps} />)
      fireEvent.click(screen.getByText('React Basics'))
      fireEvent.click(screen.getByRole('button', { name: /Start Learning/ }))

      await waitFor(() => {
        expect(defaultProps.onSelect).toHaveBeenCalledWith('topic-1')
      })
    })

    it('calls onClose when Cancel clicked', () => {
      render(<TopicSelectModal {...defaultProps} />)
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
      expect(defaultProps.onClose).toHaveBeenCalled()
    })
  })
})
