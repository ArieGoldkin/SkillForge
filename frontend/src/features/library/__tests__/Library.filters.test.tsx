import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { useLibrarySearch } from '../hooks'
import Library from '../Library'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../hooks', async () => {
  const actual = await vi.importActual<object>('../hooks')
  return {
    ...actual,
    useLibrarySearch: vi.fn().mockReturnValue({
      data: {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    }),
  }
})

const mockedUseLibrarySearch = vi.mocked(useLibrarySearch)

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

    expect(mockedUseLibrarySearch).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'complete' })
    )
  })

  it('passes status=running when selecting in-progress', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    const inProgress = screen.getByLabelText(/in progress/i)
    await user.click(inProgress)

    expect(mockedUseLibrarySearch).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'running' })
    )
  })
})
