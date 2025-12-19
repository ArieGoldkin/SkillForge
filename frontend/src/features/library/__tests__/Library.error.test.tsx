import type { LibraryListResponse } from '@app-types/library'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { createMockInfiniteQueryResult } from '@/test-utils/factories'

import { LibraryErrorAlert } from '../components/LibraryErrorAlert'
import { useLibrarySearchInfinite } from '../hooks'
import Library from '../Library'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../hooks', async () => {
  const actual = await vi.importActual<object>('../hooks')
  return {
    ...actual,
    useLibrarySearchInfinite: vi.fn(),
  }
})

const mockedUseLibrarySearchInfinite = vi.mocked(useLibrarySearchInfinite)

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
  const renderWithProviders = () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
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
    const mockRefetch = vi
      .fn()
      .mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>())

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isPending: false,
        isSuccess: false,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: mockError,
        isError: true,
        refetch: mockRefetch,
        status: 'error',
        fetchStatus: 'idle',
        isPlaceholderData: false,
        isRefetching: false,
        isStale: false,
        isPaused: false,
        failureCount: 1,
        failureReason: mockError,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
      })
    )

    renderWithProviders()

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Failed to fetch library data')).toBeInTheDocument()
  })

  it('hides error alert when isError is false', () => {
    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: { pages: [{ items: [], total: 0, limit: 20, offset: 0 }], pageParams: [0] },
        isLoading: false,
        isFetching: false,
        isPending: false,
        isSuccess: true,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: null,
        isError: false,
        refetch: vi.fn().mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>()),
        status: 'success',
        fetchStatus: 'idle',
        isPlaceholderData: false,
        isRefetching: false,
        isStale: false,
        isPaused: false,
        failureCount: 0,
        failureReason: null,
        errorUpdateCount: 0,
        errorUpdatedAt: 0,
      })
    )

    renderWithProviders()

    expect(screen.queryByText('Failed to load library')).not.toBeInTheDocument()
  })

  it('passes refetch function to LibraryErrorAlert', async () => {
    const user = userEvent.setup()
    const mockError = new Error('API error')
    const mockRefetch = vi
      .fn()
      .mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>())

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isPending: false,
        isSuccess: false,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: mockError,
        isError: true,
        refetch: mockRefetch,
        status: 'error',
        fetchStatus: 'idle',
        isPlaceholderData: false,
        isRefetching: false,
        isStale: false,
        isPaused: false,
        failureCount: 1,
        failureReason: mockError,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
      })
    )

    renderWithProviders()

    const retryButton = screen.getByRole('button', { name: /retry/i })
    await user.click(retryButton)

    expect(mockRefetch).toHaveBeenCalledTimes(1)
  })

  it('shows retrying state when isFetching is true after error', () => {
    const mockError = new Error('API error')
    const mockRefetch = vi
      .fn()
      .mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>())

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: undefined,
        isLoading: false,
        isFetching: true,
        isPending: false,
        isSuccess: false,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: mockError,
        isError: true,
        refetch: mockRefetch,
        status: 'error',
        fetchStatus: 'fetching',
        isPlaceholderData: false,
        isRefetching: true,
        isStale: false,
        isPaused: false,
        failureCount: 1,
        failureReason: mockError,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
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
    const mockRefetch = vi
      .fn()
      .mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>())

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isPending: false,
        isSuccess: false,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: mockError,
        isError: true,
        refetch: mockRefetch,
        status: 'error',
        fetchStatus: 'idle',
        isPlaceholderData: false,
        isRefetching: false,
        isStale: false,
        isPaused: false,
        failureCount: 1,
        failureReason: mockError,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
      })
    )

    renderWithProviders()

    expect(screen.getByText('Failed to load library')).toBeInTheDocument()
    expect(screen.getByText('Server returned 500 Internal Server Error')).toBeInTheDocument()
  })

  it('shows error alert even when there is partial data', () => {
    const mockError = new Error('Failed to load more results')

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: {
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
        isLoading: false,
        isFetching: false,
        isPending: false,
        isSuccess: false,
        isLoadingError: false,
        isRefetchError: false,
        isFetchNextPageError: false,
        isFetchPreviousPageError: false,
        hasNextPage: false,
        hasPreviousPage: false,
        fetchNextPage: vi.fn(),
        fetchPreviousPage: vi.fn(),
        isFetchingNextPage: false,
        isFetchingPreviousPage: false,
        error: mockError,
        isError: true,
        refetch: vi.fn().mockResolvedValue(createMockInfiniteQueryResult<LibraryListResponse>()),
        status: 'error',
        fetchStatus: 'idle',
        isPlaceholderData: false,
        isRefetching: false,
        isStale: false,
        isPaused: false,
        failureCount: 1,
        failureReason: mockError,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
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
    const mockRefetch = vi.fn(() => {
      isFetchingState = true
      // Update the mock to reflect the new state
      mockedUseLibrarySearchInfinite.mockReturnValue(
        createMockInfiniteQueryResult<LibraryListResponse>({
          data: undefined,
          isLoading: false,
          isFetching: true,
          hasNextPage: false,
          fetchNextPage: vi.fn(),
          isFetchingNextPage: false,
          error: mockError,
          isError: true,
          refetch: mockRefetch,
        })
      )
    })

    mockedUseLibrarySearchInfinite.mockReturnValue(
      createMockInfiniteQueryResult<LibraryListResponse>({
        data: undefined,
        isLoading: false,
        isFetching: isFetchingState,
        hasNextPage: false,
        fetchNextPage: vi.fn(),
        isFetchingNextPage: false,
        error: mockError,
        isError: true,
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
