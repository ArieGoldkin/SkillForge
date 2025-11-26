import type { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useTutoringMessages } from '../useTutoringMessages'

vi.mock('@services/mock.service', () => ({
  mockTutoringAPI: {
    getMessages: vi
      .fn()
      .mockResolvedValue([
        { id: '1', session_id: 'test', role: 'user', content: 'Hello', created_at: '' },
      ]),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useTutoringMessages', () => {
  it('returns initial state with loading', () => {
    const { result } = renderHook(() => useTutoringMessages('test-session'), {
      wrapper: createWrapper(),
    })

    expect(result.current.messages).toEqual([])
    expect(typeof result.current.setMessages).toBe('function')
  })

  it('loads messages from API', async () => {
    const { result } = renderHook(() => useTutoringMessages('test-session'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(1)
    })

    expect(result.current.messages[0].content).toBe('Hello')
  })
})
