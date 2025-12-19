/**
 * Tests for AnnotationQueuePage - Main page component for annotation review
 */

import type { ReactNode } from 'react'

import type { AnnotationQueueListResponse } from '@app-types/annotations'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { annotationsAPI } from '@/api/annotations'

import AnnotationQueuePage from '../AnnotationQueuePage'

// Mock the annotations API
vi.mock('@/api/annotations', () => ({
  annotationsAPI: {
    getAnnotationQueue: vi.fn(),
    markReviewed: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock TanStack Router Link component
vi.mock('@tanstack/react-router', () => ({
  Link: ({
    to,
    params,
    children,
    className,
  }: {
    to: string
    params: { artifactId: string }
    children: ReactNode
    className?: string
  }) => (
    <a href={`${to.replace('$artifactId', params.artifactId)}`} className={className}>
      {children}
    </a>
  ),
}))

// Create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('AnnotationQueuePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading state', () => {
    it('shows loading message while fetching data', () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      expect(screen.getByText('Loading annotation queue...')).toBeInTheDocument()
    })

    it('shows page header during loading', () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      expect(screen.getByText('Annotation Review Queue')).toBeInTheDocument()
      expect(
        screen.getByText('Review flagged artifacts and mark them as reviewed')
      ).toBeInTheDocument()
    })
  })

  describe('Error state', () => {
    it('displays error message when API fails', async () => {
      const mockError = new Error('Failed to fetch queue')
      vi.mocked(annotationsAPI.getAnnotationQueue).mockRejectedValueOnce(mockError)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Error loading queue')).toBeInTheDocument()
        expect(screen.getByText('Failed to fetch queue')).toBeInTheDocument()
      })
    })

    it('shows generic error message for non-Error objects', async () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockRejectedValueOnce('String error')

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Error loading queue')).toBeInTheDocument()
        expect(screen.getByText('An error occurred while loading the queue')).toBeInTheDocument()
      })
    })
  })

  describe('Data rendering', () => {
    it('displays queue items in table', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T10:00:00Z',
            reviewed_at: null,
          },
          {
            id: 2,
            artifact_id: 'artifact-456',
            reason: 'Incorrect information',
            status: 'reviewed',
            created_at: '2024-01-02T10:00:00Z',
            reviewed_at: '2024-01-02T11:00:00Z',
          },
        ],
        total: 2,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Poor quality')).toBeInTheDocument()
        expect(screen.getByText('Incorrect information')).toBeInTheDocument()
      })

      // Both items should have truncated artifact IDs
      const artifactCells = screen.getAllByText(/artifact\.\.\./i)
      expect(artifactCells).toHaveLength(2)
    })

    it('shows empty state when no items', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('No items in the review queue.')).toBeInTheDocument()
      })
    })

    it('truncates long artifact IDs', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123456789-very-long-id',
            reason: 'Test',
            status: 'pending',
            created_at: '2024-01-01T10:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        // Should show first 8 chars + "..."
        expect(screen.getByText(/artifact\.\.\./i)).toBeInTheDocument()
      })
    })
  })

  describe('Filter switching', () => {
    it('defaults to pending filter', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 0,
          status: 'pending',
        })
      })
    })

    it('switches to all filter when clicked', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      // TabsTrigger renders as a button with role="tab"
      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 0,
          status: undefined,
        })
      })
    })

    it('switches to reviewed filter when clicked', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      const reviewedTab = screen.getByRole('tab', { name: /reviewed/i })
      await user.click(reviewedTab)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 0,
          status: 'reviewed',
        })
      })
    })

    it('resets offset when changing filter', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 50,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      // Go to next page (offset = 20)
      const nextButton = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 20,
          status: 'pending',
        })
      })

      // Change filter - should reset offset to 0
      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 0,
          status: undefined,
        })
      })
    })
  })

  describe('Pagination controls', () => {
    it('shows pagination when there are multiple pages', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: new Array(20).fill(null).map((_, i) => ({
          id: i + 1,
          artifact_id: `artifact-${i}`,
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        })),
        total: 50,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
      })

      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    })

    it('navigates to next page', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 50,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      const nextButton = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 20,
          status: 'pending',
        })
      })
    })

    it('navigates to previous page', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 50,
        limit: 20,
        offset: 20,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      const prevButton = screen.getByRole('button', { name: /previous/i })
      await user.click(prevButton)

      await waitFor(() => {
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledWith({
          limit: 20,
          offset: 0,
          status: 'pending',
        })
      })
    })

    it('disables previous button on first page', async () => {
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 50,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValueOnce(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      const prevButton = screen.getByRole('button', { name: /previous/i })
      expect(prevButton).toBeDisabled()
    })

    it('disables next button on last page', async () => {
      const user = userEvent.setup()
      // First page
      const firstPageResponse: AnnotationQueueListResponse = {
        items: [],
        total: 41, // Total just over 2 pages (41 items, 20 per page = 3 pages, last has 1 item)
        limit: 20,
        offset: 0,
      }
      // Second page
      const secondPageResponse: AnnotationQueueListResponse = {
        items: [],
        total: 41,
        limit: 20,
        offset: 20,
      }
      // Third/last page
      const lastPageResponse: AnnotationQueueListResponse = {
        items: [],
        total: 41,
        limit: 20,
        offset: 40,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue)
        .mockResolvedValueOnce(firstPageResponse)
        .mockResolvedValueOnce(secondPageResponse)
        .mockResolvedValueOnce(lastPageResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      // Navigate to page 2
      const nextButton1 = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton1)

      await waitFor(() => {
        expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
      })

      // Navigate to page 3 (last page)
      const nextButton2 = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton2)

      await waitFor(() => {
        expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
      })

      // On last page, next button should be disabled
      await waitFor(() => {
        const nextButton = screen.getByRole('button', { name: /next/i })
        expect(nextButton).toBeDisabled()
      })
    })
  })

  describe('Refresh button', () => {
    it('refetches data when clicked', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.queryByText('Loading annotation queue...')).not.toBeInTheDocument()
      })

      const refreshButton = screen.getByRole('button', { name: /refresh/i })
      await user.click(refreshButton)

      await waitFor(() => {
        // Should be called twice: initial load + manual refresh
        expect(annotationsAPI.getAnnotationQueue).toHaveBeenCalledTimes(2)
      })
    })

    it('disables refresh button during loading', () => {
      vi.mocked(annotationsAPI.getAnnotationQueue).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      const refreshButton = screen.getByRole('button', { name: /refresh/i })
      expect(refreshButton).toBeDisabled()
    })
  })

  describe('Mark as reviewed', () => {
    it('calls markReviewed when button clicked', async () => {
      const user = userEvent.setup()
      const mockResponse: AnnotationQueueListResponse = {
        items: [
          {
            id: 1,
            artifact_id: 'artifact-123',
            reason: 'Poor quality',
            status: 'pending',
            created_at: '2024-01-01T10:00:00Z',
            reviewed_at: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }

      vi.mocked(annotationsAPI.getAnnotationQueue).mockResolvedValue(mockResponse)
      vi.mocked(annotationsAPI.markReviewed).mockResolvedValueOnce({
        status: 'success',
        message: 'Marked as reviewed',
      })

      render(<AnnotationQueuePage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Poor quality')).toBeInTheDocument()
      })

      const markButton = screen.getByRole('button', { name: /mark reviewed/i })
      await user.click(markButton)

      await waitFor(() => {
        expect(annotationsAPI.markReviewed).toHaveBeenCalledWith(1)
      })
    })
  })
})
