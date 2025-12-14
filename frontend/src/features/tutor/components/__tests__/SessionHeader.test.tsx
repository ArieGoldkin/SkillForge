import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SessionHeader } from '../SessionHeader'

// Mock tanstack router
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

// Mock the mock service
vi.mock('@services/mock.service', () => ({
  mockTutoringAPI: {
    endSession: vi.fn().mockResolvedValue({
      id: 'test-session-id',
      status: 'completed',
      completed_at: new Date().toISOString(),
    }),
  },
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('SessionHeader', () => {
  const defaultProps = {
    sessionId: 'test-session-id',
    analysisId: 'test-analysis-id',
  }

  it('renders session header with title and description', () => {
    renderWithProviders(<SessionHeader {...defaultProps} />)

    expect(screen.getByText('Socratic Tutoring Session')).toBeInTheDocument()
    expect(screen.getByText(/Interactive learning with AI guidance/i)).toBeInTheDocument()
  })

  it('renders Exit Tutoring button', () => {
    renderWithProviders(<SessionHeader {...defaultProps} />)

    const exitButton = screen.getByTestId('exit-tutoring-button')
    expect(exitButton).toBeInTheDocument()
    expect(exitButton).toHaveTextContent('Exit Tutoring')
  })

  it('opens confirmation dialog when Exit Tutoring is clicked', async () => {
    renderWithProviders(<SessionHeader {...defaultProps} />)

    await userEvent.click(screen.getByTestId('exit-tutoring-button'))

    await waitFor(() => {
      expect(screen.getByText('Exit Tutoring Session?')).toBeInTheDocument()
    })
  })

  it('closes dialog when Cancel is clicked', async () => {
    renderWithProviders(<SessionHeader {...defaultProps} />)

    await userEvent.click(screen.getByTestId('exit-tutoring-button'))
    await waitFor(() => {
      expect(screen.getByText('Exit Tutoring Session?')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByTestId('cancel-exit-button'))

    await waitFor(() => {
      expect(screen.queryByText('Exit Tutoring Session?')).not.toBeInTheDocument()
    })
  })
})
