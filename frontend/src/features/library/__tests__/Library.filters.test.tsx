import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { useLibrarySearchInfinite } from '../hooks'
import Library from '../Library'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../hooks', async () => {
  const actual = await vi.importActual<object>('../hooks')
  return {
    ...actual,
    useLibrarySearchInfinite: vi.fn().mockReturnValue({
      data: { pages: [{ items: [], total: 0, limit: 20, offset: 0 }] },
      isLoading: false,
      isFetching: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    }),
  }
})

const mockedUseLibrarySearchInfinite = vi.mocked(useLibrarySearchInfinite)

describe('Library filters', () => {
  const renderWithProviders = () => {
    const client = new QueryClient()
    return render(
      <QueryClientProvider client={client}>
        <Library />
      </QueryClientProvider>
    )
  }

  it('passes status=complete when selecting completed', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    const completed = screen.getByLabelText(/completed/i, { selector: '#status-completed' })
    await user.click(completed)

    expect(mockedUseLibrarySearchInfinite).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'complete' })
    )
  })

  it('passes status=running when selecting in-progress', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    const inProgress = screen.getByLabelText(/in progress/i)
    await user.click(inProgress)

    expect(mockedUseLibrarySearchInfinite).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'running' })
    )
  })
})
