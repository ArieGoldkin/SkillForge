/**
 * Unified tutor chat hook using React 19's useOptimistic for instant message display.
 * Combines message fetching and sending with optimistic UI updates.
 */

import { useOptimistic, useTransition } from 'react'

import type { TutoringMessage } from '@app-types/api'
import { useToast } from '@hooks/use-toast'
import { useQuery } from '@tanstack/react-query'

import { TIME_CONSTANTS } from '@/lib/constants'

import { mockTutoringAPI } from '@services/mock.service'

interface UseTutorChatOptions {
  sessionId: string
}

/**
 * Custom hook for tutor chat with optimistic message updates.
 * Messages appear instantly before API confirmation.
 */
// eslint-disable-next-line max-lines-per-function
export function useTutorChat({ sessionId }: UseTutorChatOptions) {
  const { toast } = useToast()

  // Fetch initial messages from API
  const {
    data: confirmedMessages = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['tutoring-messages', sessionId],
    queryFn: () => mockTutoringAPI.getMessages(sessionId),
  })

  // Optimistic state - shows messages instantly before API confirms
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    confirmedMessages,
    (currentMessages, newMessage: TutoringMessage) => [...currentMessages, newMessage]
  )

  const [isPending, startTransition] = useTransition()

  /**
   * Send a message with optimistic UI update.
   * Message appears instantly, API call happens in background.
   * Automatically rolls back on failure.
   */
  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    // Create optimistic user message
    const optimisticUserMessage: TutoringMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
    }

    startTransition(async () => {
      // Instant UI update - user sees message immediately
      addOptimisticMessage(optimisticUserMessage)

      try {
        // API call to persist message
        await mockTutoringAPI.sendMessage(sessionId, content.trim())

        // Simulate assistant response after delay
        setTimeout(() => {
          const assistantMessage: TutoringMessage = {
            id: `temp-${Date.now()}`,
            session_id: sessionId,
            role: 'assistant',
            content:
              "That's a great question! Let me help you understand that concept better. What specific aspect would you like to explore?",
            created_at: new Date().toISOString(),
          }

          // Add assistant message optimistically
          startTransition(async () => {
            addOptimisticMessage(assistantMessage)
          })
        }, TIME_CONSTANTS.MOCK_API_DELAY)
      } catch (error) {
        // useOptimistic automatically rolls back the optimistic update
        toast({
          title: 'Failed to send message',
          description: error instanceof Error ? error.message : 'An error occurred',
          variant: 'destructive',
        })
      }
    })
  }

  return {
    /**
     * Messages array with optimistic updates.
     * Shows user's message instantly before API confirmation.
     */
    messages: optimisticMessages,

    /**
     * Send a message with instant UI feedback.
     * @param content - The message content to send
     */
    sendMessage,

    /**
     * True while a message is being sent (pending API response).
     * Used to disable input during send.
     */
    isPending,

    /**
     * True while initial messages are being loaded.
     * Used for skeleton loading state.
     */
    isLoading,

    /**
     * Error from fetching messages, if any.
     */
    error,
  }
}
