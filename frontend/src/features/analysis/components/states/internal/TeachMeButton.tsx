/**
 * TeachMeButton - Entry point for tutoring sessions
 *
 * Opens TopicSelectModal to let users choose a topic,
 * then creates a session and navigates to the tutor page.
 *
 * Gets analysisId and title from Zustand store (Issue #396)
 * instead of props, eliminating prop drilling.
 */
import { useState, useCallback } from 'react'

import { selectAnalysisId, selectAnalysisMetadata, useSSEStore } from '@stores/sseStore'
import { GraduationCap } from 'lucide-react'

import { TopicSelectModal } from '@features/tutor/components'
import { useStartTutoring } from '@features/tutor/hooks/useStartTutoring'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

interface TeachMeButtonProps {
  /** UI-only props - control appearance */
  isCompact?: boolean
  variant?: 'default' | 'outline'
}

/**
 * Custom hook to manage topic selection modal state
 * Extracted to keep TeachMeButton component focused on rendering
 */
function useTopicModal(analysisId: string | null) {
  const [isOpen, setIsOpen] = useState(false)

  const { topics, isLoadingTopics, fetchTopics, startTutoring } = useStartTutoring({
    analysisId: analysisId ?? '',
    onError: (error) => console.error('Tutoring error:', error),
  })

  const open = useCallback(async () => {
    if (!analysisId) return
    setIsOpen(true)
    await fetchTopics()
  }, [analysisId, fetchTopics])

  const close = useCallback(() => setIsOpen(false), [])

  const selectTopic = useCallback(
    async (topicId: string) => {
      await startTutoring(topicId)
      setIsOpen(false)
    },
    [startTutoring]
  )

  return { isOpen, topics, isLoadingTopics, open, close, selectTopic }
}

export function TeachMeButton({ isCompact = false, variant = 'outline' }: TeachMeButtonProps) {
  // Get data from store instead of props (Issue #396)
  const analysisId = useSSEStore(selectAnalysisId)
  const analysisMetadata = useSSEStore(selectAnalysisMetadata)
  const modal = useTopicModal(analysisId)

  // Don't render if no analysis available
  if (!analysisId) return null

  return (
    <>
      <Button
        variant={variant}
        size={isCompact ? 'default' : 'lg'}
        onClick={modal.open}
        className="gap-2"
        data-testid="teach-me-button"
      >
        <GraduationCap className={cn(isCompact ? 'h-4 w-4' : 'h-5 w-5')} />
        Teach Me
      </Button>

      <TopicSelectModal
        isOpen={modal.isOpen}
        onClose={modal.close}
        onSelect={modal.selectTopic}
        topics={modal.topics}
        isLoading={modal.isLoadingTopics}
        analysisTitle={analysisMetadata?.title}
      />
    </>
  )
}
