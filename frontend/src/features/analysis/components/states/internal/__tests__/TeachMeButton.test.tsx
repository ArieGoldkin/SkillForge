import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { TeachMeButton } from '../TeachMeButton'

vi.mock('@features/tutor/hooks/useStartTutoring', () => ({
  useStartTutoring: vi.fn(() => ({
    topics: [
      { id: 'topic-1', name: 'React Basics', description: 'Learn React' },
      { id: 'topic-2', name: 'TypeScript', description: 'Type safety' },
    ],
    isLoadingTopics: false,
    fetchTopics: vi.fn(),
    startTutoring: vi.fn(),
  })),
}))

describe('TeachMeButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders button with Teach Me text', () => {
      render(<TeachMeButton analysisId="test-123" />)
      expect(screen.getByTestId('teach-me-button')).toBeInTheDocument()
      expect(screen.getByText('Teach Me')).toBeInTheDocument()
    })

    it('renders with large size by default', () => {
      render(<TeachMeButton analysisId="test-123" />)
      const button = screen.getByTestId('teach-me-button')
      expect(button).toHaveClass('gap-2')
    })

    it('renders with outline variant by default', () => {
      render(<TeachMeButton analysisId="test-123" variant="outline" />)
      const button = screen.getByTestId('teach-me-button')
      expect(button).toBeInTheDocument()
    })
  })

  describe('Modal Behavior', () => {
    it('opens modal when clicked', async () => {
      render(<TeachMeButton analysisId="test-123" />)
      fireEvent.click(screen.getByTestId('teach-me-button'))

      await waitFor(() => {
        expect(screen.getByText('Start Tutoring Session')).toBeInTheDocument()
      })
    })

    it('passes analysisTitle to modal', async () => {
      render(<TeachMeButton analysisId="test-123" analysisTitle="My Analysis" />)
      fireEvent.click(screen.getByTestId('teach-me-button'))

      await waitFor(() => {
        expect(screen.getByText(/Select a topic from "My Analysis"/)).toBeInTheDocument()
      })
    })
  })
})
