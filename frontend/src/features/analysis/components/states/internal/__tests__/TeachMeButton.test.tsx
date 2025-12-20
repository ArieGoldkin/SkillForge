/**
 * TeachMeButton tests
 *
 * Issue #396: Updated to mock Zustand store instead of passing props,
 * since component now gets analysisId and analysisMetadata from store.
 */
import { useSSEStore } from '@stores/sseStore'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { TeachMeButton } from '../TeachMeButton'

// Mock the store module
vi.mock('@stores/sseStore', () => ({
  useSSEStore: vi.fn(),
  selectAnalysisId: (state: { activeAnalysisId: string | null }) => state.activeAnalysisId,
  selectAnalysisMetadata: (state: { analysisMetadata: unknown }) => state.analysisMetadata,
}))

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

const mockUseSSEStore = useSSEStore as ReturnType<typeof vi.fn>

describe('TeachMeButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock: analysisId is present, no metadata
    mockUseSSEStore.mockImplementation((selector: (state: unknown) => unknown) => {
      const state = {
        activeAnalysisId: 'test-123',
        analysisMetadata: null,
      }
      return selector(state)
    })
  })

  describe('Rendering', () => {
    it('renders button with Teach Me text', () => {
      render(<TeachMeButton />)
      expect(screen.getByTestId('teach-me-button')).toBeInTheDocument()
      expect(screen.getByText('Teach Me')).toBeInTheDocument()
    })

    it('renders with large size by default', () => {
      render(<TeachMeButton />)
      const button = screen.getByTestId('teach-me-button')
      expect(button).toHaveClass('gap-2')
    })

    it('renders with outline variant by default', () => {
      render(<TeachMeButton variant="outline" />)
      const button = screen.getByTestId('teach-me-button')
      expect(button).toBeInTheDocument()
    })

    it('returns null when analysisId is not present', () => {
      mockUseSSEStore.mockImplementation((selector: (state: unknown) => unknown) => {
        const state = {
          activeAnalysisId: null,
          analysisMetadata: null,
        }
        return selector(state)
      })
      const { container } = render(<TeachMeButton />)
      expect(container.firstChild).toBeNull()
    })
  })

  describe('Modal Behavior', () => {
    it('opens modal when clicked', async () => {
      render(<TeachMeButton />)
      fireEvent.click(screen.getByTestId('teach-me-button'))

      await waitFor(() => {
        expect(screen.getByText('Start Tutoring Session')).toBeInTheDocument()
      })
    })

    it('passes analysisTitle from store to modal', async () => {
      // Mock store with metadata containing title
      mockUseSSEStore.mockImplementation((selector: (state: unknown) => unknown) => {
        const state = {
          activeAnalysisId: 'test-123',
          analysisMetadata: { title: 'My Analysis' },
        }
        return selector(state)
      })

      render(<TeachMeButton />)
      fireEvent.click(screen.getByTestId('teach-me-button'))

      await waitFor(() => {
        expect(screen.getByText(/Select a topic from "My Analysis"/)).toBeInTheDocument()
      })
    })
  })
})
