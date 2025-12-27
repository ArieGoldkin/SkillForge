/**
 * Tests for useTutorChat - React 19 useOptimistic Pattern
 *
 * This test suite verifies:
 * 1. Optimistic message display (instant UI updates)
 * 2. Automatic rollback on API failure
 * 3. Transition state management (isPending)
 * 4. Integration with TanStack Query
 *
 * @tags @unit @react19
 */

import type { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { useTutorChat } from '../useTutorChat'

// Mock the toast hook
const mockToast = vi.fn()
vi.mock('@hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

// Mock API responses
const mockGetMessages = vi.fn()
const mockSendMessage = vi.fn()

vi.mock('@services/mock.service', () => ({
  mockTutoringAPI: {
    getMessages: (...args: unknown[]) => mockGetMessages(...args),
    sendMessage: (...args: unknown[]) => mockSendMessage(...args),
  },
}))

// Mock TIME_CONSTANTS
vi.mock('@/lib/constants', () => ({
  TIME_CONSTANTS: {
    MOCK_API_DELAY: 100,
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useTutorChat - React 19 useOptimistic', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetMessages.mockResolvedValue([])
    mockSendMessage.mockResolvedValue({
      id: 'msg-api-1',
      session_id: 'test-session',
      role: 'user',
      content: 'Test message',
      created_at: new Date().toISOString(),
    })
  })

  describe('Initial State', () => {
    it('should return empty messages initially', () => {
      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      expect(result.current.messages).toEqual([])
      expect(result.current.isPending).toBe(false)
      expect(result.current.isLoading).toBe(true)
    })

    it('should fetch messages on mount', async () => {
      const existingMessages = [
        {
          id: 'msg-1',
          session_id: 'test-session',
          role: 'user' as const,
          content: 'Previous message',
          created_at: '2025-01-15T10:00:00Z',
        },
      ]
      mockGetMessages.mockResolvedValue(existingMessages)

      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.messages).toEqual(existingMessages)
      expect(mockGetMessages).toHaveBeenCalledWith('test-session')
    })
  })

  describe('Optimistic Updates', () => {
    it('should show message instantly before API responds', async () => {
      // Make API slow so we can observe optimistic update
      mockSendMessage.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  id: 'msg-api-1',
                  session_id: 'test-session',
                  role: 'user',
                  content: 'Hello',
                  created_at: new Date().toISOString(),
                }),
              500
            )
          )
      )

      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Send message
      act(() => {
        result.current.sendMessage('Hello')
      })

      // Message should appear INSTANTLY (optimistic)
      await waitFor(() => {
        expect(result.current.messages.length).toBe(1)
      })

      // Verify optimistic message properties
      const optimisticMessage = result.current.messages[0]
      expect(optimisticMessage.content).toBe('Hello')
      expect(optimisticMessage.role).toBe('user')
      expect(optimisticMessage.id).toMatch(/^temp-/)
    })

    it('should generate temporary ID for optimistic messages', async () => {
      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.sendMessage('Test')
      })

      await waitFor(() => {
        expect(result.current.messages.length).toBe(1)
      })

      expect(result.current.messages[0].id).toMatch(/^temp-\d+$/)
    })
  })

  describe('Error Handling', () => {
    it('should rollback optimistic update on API failure', async () => {
      mockSendMessage.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.sendMessage('Will fail')
      })

      // Message appears optimistically first
      await waitFor(() => {
        expect(result.current.messages.length).toBe(1)
      })

      // After error, useOptimistic rolls back automatically
      await waitFor(() => {
        expect(result.current.messages.length).toBe(0)
      })
    })

    it('should show toast notification on error', async () => {
      mockSendMessage.mockRejectedValue(new Error('Failed to send'))

      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.sendMessage('Will fail')
      })

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Failed to send message',
          description: 'Failed to send',
          variant: 'destructive',
        })
      })
    })
  })

  describe('Transition State', () => {
    it('should set isPending during message send', async () => {
      let resolvePromise: () => void
      mockSendMessage.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = () =>
              resolve({
                id: 'msg-1',
                session_id: 'test-session',
                role: 'user',
                content: 'Test',
                created_at: new Date().toISOString(),
              })
          })
      )

      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isPending).toBe(false)

      act(() => {
        result.current.sendMessage('Test')
      })

      // isPending should be true during transition
      await waitFor(() => {
        expect(result.current.isPending).toBe(true)
      })

      // Resolve the promise
      act(() => {
        resolvePromise!()
      })

      // isPending should become false after resolution
      await waitFor(() => {
        expect(result.current.isPending).toBe(false)
      })
    })
  })

  describe('Input Validation', () => {
    it('should not send empty messages', async () => {
      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.sendMessage('')
        result.current.sendMessage('   ')
      })

      expect(mockSendMessage).not.toHaveBeenCalled()
      expect(result.current.messages.length).toBe(0)
    })

    it('should trim whitespace from messages', async () => {
      const { result } = renderHook(() => useTutorChat({ sessionId: 'test-session' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.sendMessage('  Hello World  ')
      })

      await waitFor(() => {
        expect(result.current.messages.length).toBeGreaterThan(0)
        expect(result.current.messages[0].content).toBe('Hello World')
      })

      expect(mockSendMessage).toHaveBeenCalledWith('test-session', 'Hello World')
    })
  })

  describe('Session Integration', () => {
    it('should use correct session ID for API calls', async () => {
      const { result } = renderHook(() => useTutorChat({ sessionId: 'custom-session-123' }), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(mockGetMessages).toHaveBeenCalledWith('custom-session-123')

      act(() => {
        result.current.sendMessage('Test')
      })

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith('custom-session-123', 'Test')
      })
    })
  })
})

/**
 * TESTING BEST PRACTICES FOR useOptimistic
 *
 * 1. Test optimistic state appears immediately
 *    - Don't wait for API, verify instant update
 *
 * 2. Test rollback on failure
 *    - Mock API to reject
 *    - Verify state reverts to previous
 *
 * 3. Test transition state (isPending)
 *    - Verify true during async operation
 *    - Verify false after completion
 *
 * 4. Test with slow APIs
 *    - Use delayed mocks to observe intermediate states
 *
 * 5. Use act() for state updates
 *    - Wrap sendMessage calls in act()
 *    - Ensures React flushes updates
 *
 * 6. Use waitFor() for async assertions
 *    - State updates are async in React 19
 *    - Don't assert synchronously
 */
