/**
 * useStartTutoring - Hook to handle tutoring session initialization
 */

import { useState, useCallback } from 'react'

import type { TutoringTopic } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { mockTutoringAPI } from '@services/mock.service'

interface UseStartTutoringOptions {
  analysisId: string
  onError?: (error: string) => void
}

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback

export function useStartTutoring({ analysisId, onError }: UseStartTutoringOptions) {
  const navigate = useNavigate()
  const [topics, setTopics] = useState<TutoringTopic[]>([])
  const [isLoadingTopics, setIsLoadingTopics] = useState(false)

  const fetchTopics = useCallback(async () => {
    setIsLoadingTopics(true)
    try {
      setTopics(await mockTutoringAPI.getTopics(analysisId))
    } catch (error) {
      onError?.(getErrorMessage(error, 'Failed to fetch topics'))
    } finally {
      setIsLoadingTopics(false)
    }
  }, [analysisId, onError])

  const startTutoring = useCallback(
    async (topicId: string) => {
      try {
        const session = await mockTutoringAPI.createSession(analysisId, topicId)
        navigate({ to: '/tutor/$sessionId', params: { sessionId: session.id } })
      } catch (error) {
        onError?.(getErrorMessage(error, 'Failed to create session'))
      }
    },
    [analysisId, navigate, onError]
  )

  return { topics, isLoadingTopics, fetchTopics, startTutoring }
}
