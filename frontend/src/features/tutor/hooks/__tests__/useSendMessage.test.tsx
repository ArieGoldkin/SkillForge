import type { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useSendMessage } from '../useSendMessage'

const mockSendMessage = vi.fn().mockResolvedValue({
  id: 'msg-1',
  session_id: 'test',
  role: 'user',
  content: 'Test message',
  created_at: new Date().toISOString(),
})

vi.mock('@services/mock.service', () => ({
  mockTutoringAPI: {
    sendMessage: (...args: unknown[]) => mockSendMessage(...args),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useSendMessage', () => {
  it('returns mutation object', () => {
    const setMessages = vi.fn()
    const { result } = renderHook(
      () => useSendMessage({ sessionId: 'test', messages: [], setMessages }),
      { wrapper: createWrapper() }
    )

    expect(result.current.mutate).toBeDefined()
    expect(result.current.isPending).toBe(false)
  })

  it('calls API and updates messages on success', async () => {
    const setMessages = vi.fn()
    const { result } = renderHook(
      () => useSendMessage({ sessionId: 'test', messages: [], setMessages }),
      { wrapper: createWrapper() }
    )

    act(() => {
      result.current.mutate('Hello')
    })

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('test', 'Hello')
    })

    await waitFor(() => {
      expect(setMessages).toHaveBeenCalled()
    })
  })
})
