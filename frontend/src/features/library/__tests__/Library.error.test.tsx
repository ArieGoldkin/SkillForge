import type { AnalysisStatus } from '@app-types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { LibraryErrorAlert } from '../components/LibraryErrorAlert'
import { useLibraryData, useLibraryState, useLibraryFilters } from '../hooks'
import Library from '../Library'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../hooks/useLibraryData', () => ({
  useLibraryData: vi.fn(),
}))

vi.mock('../hooks/useLibraryState', () => ({
  useLibraryState: vi.fn(),
}))

vi.mock('../hooks/useLibraryFilters', () => ({
  useLibraryFilters: vi.fn(),
  useInitialFilters: () => ({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 120],
  }),
}))

const mockedUseLibraryData = vi.mocked(useLibraryData)
const mockedUseLibraryState = vi.mocked(useLibraryState)
const mockedUseLibraryFilters = vi.mocked(useLibraryFilters)

describe('LibraryErrorAlert Component', () => {
  it('renders error message from Error object', () => {
    const error = new Error('Network connection failed')
    const onRetry = vi.fn()

    render(<LibraryErrorAlert error={error} onRetry={onRetry} isRetrying={false} />)

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Network connection failed')).toBeInTheDocument()
  })

  it('renders fallback message for non-Error object', () => {
    const onRetry = vi.fn()

    render(<LibraryErrorAlert error={null} onRetry={onRetry} isRetrying={false} />)

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(
      screen.getByText('Unable to connect to the server. Please check your connection.')
    ).toBeInTheDocument()
  })

  it('retry button calls onRetry when clicked', async () => {
    const user = userEvent.setup()
    const error = new Error('Test error')
    const onRetry = vi.fn()

    render(<LibraryErrorAlert error={error} onRetry={onRetry} isRetrying={false} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    await user.click(retryButton)

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('shows spinner when isRetrying is true', () => {
    const error = new Error('Test error')
    const onRetry = vi.fn()

    render(<LibraryErrorAlert error={error} onRetry={onRetry} isRetrying={true} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeDisabled()

    // Check for the spinning icon by looking for the animate-spin class
    const spinningIcon = retryButton.querySelector('.animate-spin')
    expect(spinningIcon).toBeInTheDocument()
  })

  it('retry button is enabled when not retrying', () => {
    const error = new Error('Test error')
    const onRetry = vi.fn()

    render(<LibraryErrorAlert error={error} onRetry={onRetry} isRetrying={false} />)

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).not.toBeDisabled()
  })
})

describe('Library Component - Error Handling', () => {
  const createMockLibraryData = (overrides?: Partial<ReturnType<typeof useLibraryData>>) => {
    return {
      filteredSkills: [],
      availableTags: [],
      availableStatuses: [] as AnalysisStatus[],
      showingCount: 0,
      totalCount: 0,
      isLoading: false,
      isFetching: false,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      searchError: null,
      isError: false,
      refetch: vi.fn().mockResolvedValue({
        data: { pages: [], pageParams: [] },
        error: null,
        isError: false,
        isLoading: false,
        isSuccess: true,
      } as never),
      searchResults: undefined,
      ...overrides,
    }
  }

  const renderWithProviders = () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    // Setup default mocks
    mockedUseLibraryState.mockReturnValue({
      searchQuery: '',
      setSearchQuery: vi.fn(),
      searchMode: 'hybrid',
      setSearchMode: vi.fn(),
      showCompletedOnly: true,
      setShowCompletedOnly: vi.fn(),
      filters: {
        difficulty: [],
        tags: [],
        status: [],
        durationRange: [0, 120],
      },
      setFilters: vi.fn(),
    })

    mockedUseLibraryFilters.mockReturnValue({
      handleFiltersChange: vi.fn(),
    })

    return render(
      <QueryClientProvider client={client}>
        <Library />
      </QueryClientProvider>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows LibraryErrorAlert when isError is true', () => {
    const mockError = new Error('Failed to fetch library data')
    const mockRefetch = vi.fn()

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        refetch: mockRefetch,
      })
    )

    renderWithProviders()

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Failed to fetch library data')).toBeInTheDocument()
  })

  it('hides error alert when isError is false', () => {
    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: null,
        isError: false,
        searchResults: {
          pages: [{ items: [], total: 0, limit: 20, offset: 0 }],
          pageParams: [0],
        },
      })
    )

    renderWithProviders()

    expect(screen.queryByText('Failed to load library')).not.toBeInTheDocument()
  })

  it('passes refetch function to LibraryErrorAlert', async () => {
    const user = userEvent.setup()
    const mockError = new Error('API error')
    const mockRefetch = vi.fn().mockResolvedValue({
      data: { pages: [], pageParams: [] },
      error: null,
      isError: false,
      isLoading: false,
      isSuccess: true,
    } as never)

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        refetch: mockRefetch,
      })
    )

    renderWithProviders()

    const retryButton = screen.getByRole('button', { name: /retry/i })
    await user.click(retryButton)

    expect(mockRefetch).toHaveBeenCalledTimes(1)
  })

  it('shows retrying state when isFetching is true after error', () => {
    const mockError = new Error('API error')
    const mockRefetch = vi.fn().mockResolvedValue({
      data: { pages: [], pageParams: [] },
      error: null,
      isError: false,
      isLoading: false,
      isSuccess: true,
    } as never)

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        isFetching: true,
        refetch: mockRefetch,
      })
    )

    renderWithProviders()

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeDisabled()

    // Verify spinning icon is present
    const spinningIcon = retryButton.querySelector('.animate-spin')
    expect(spinningIcon).toBeInTheDocument()
  })

  it('handles error with custom error message', () => {
    const mockError = new Error('Server returned 500 Internal Server Error')
    const mockRefetch = vi.fn()

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        refetch: mockRefetch,
      })
    )

    renderWithProviders()

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Server returned 500 Internal Server Error')).toBeInTheDocument()
  })

  it('shows error alert even when there is partial data', () => {
    const mockError = new Error('Failed to load more results')

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        searchResults: {
          pages: [
            {
              items: [
                {
                  analysis_id: '1',
                  title: 'Test Analysis',
                  content_type: 'article',
                  status: 'complete',
                  created_at: '2025-01-01T00:00:00Z',
                  url: 'https://example.com',
                  tags: [],
                  snippet: 'test snippet',
                  rank: 1,
                },
              ],
              total: 1,
              limit: 20,
              offset: 0,
            },
          ],
          pageParams: [0],
        },
        filteredSkills: [
          {
            id: '1',
            title: 'Test Analysis',
            description: 'test snippet',
            thumbnail: 'https://api.dicebear.com/7.x/shapes/svg?seed=1',
            duration: 25,
            difficulty: 'intermediate' as const,
            tags: ['article'],
            progress: 0,
            status: 'completed' as const,
            analysisStatus: 'complete' as const,
            onSelect: vi.fn(),
          },
        ],
        showingCount: 1,
        totalCount: 1,
        refetch: vi.fn(),
      })
    )

    renderWithProviders()

    // Error alert should be visible
    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Failed to load more results')).toBeInTheDocument()

    // Content should also be visible
    expect(screen.getByText('Test Analysis')).toBeInTheDocument()
  })

  it('retrying state changes from false to true when refetching', async () => {
    const user = userEvent.setup()
    const mockError = new Error('API error')
    let isFetchingState = false
    const mockRefetch = vi.fn().mockImplementation(() => {
      isFetchingState = true
      // Update the mock to reflect the new state
      mockedUseLibraryData.mockReturnValue(
        createMockLibraryData({
          searchError: mockError,
          isError: true,
          isFetching: true,
          refetch: mockRefetch,
        })
      )
      return Promise.resolve({
        data: { pages: [], pageParams: [] },
        error: null,
        isError: false,
        isLoading: false,
        isSuccess: true,
      } as never)
    })

    mockedUseLibraryData.mockReturnValue(
      createMockLibraryData({
        searchError: mockError,
        isError: true,
        isFetching: isFetchingState,
        refetch: mockRefetch,
      })
    )

    const { rerender } = renderWithProviders()

    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).not.toBeDisabled()

    await user.click(retryButton)

    // Re-render to reflect the state change
    rerender(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <Library />
      </QueryClientProvider>
    )

    await waitFor(() => {
      const updatedRetryButton = screen.getByRole('button', { name: /retry/i })
      expect(updatedRetryButton).toBeDisabled()
    })
  })
})
