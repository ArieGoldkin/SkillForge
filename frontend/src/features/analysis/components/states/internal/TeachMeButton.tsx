/**
 * TeachMeButton - Entry point for tutoring sessions
 *
 * Opens TopicSelectModal to let users choose a topic,
 * then creates a session and navigates to the tutor page.
 */

import { useState, useCallback } from 'react'

import { GraduationCap } from 'lucide-react'

import { TopicSelectModal } from '@features/tutor/components'
import { useStartTutoring } from '@features/tutor/hooks/useStartTutoring'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

interface TeachMeButtonProps {
  analysisId: string
  analysisTitle?: string
  isCompact?: boolean
  variant?: 'default' | 'outline'
}

export function TeachMeButton({
  analysisId,
  analysisTitle,
  isCompact = false,
  variant = 'outline',
}: TeachMeButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { topics, isLoadingTopics, fetchTopics, startTutoring } = useStartTutoring({
    analysisId,
    onError: (error) => console.error('Tutoring error:', error),
  })

  const handleOpenModal = useCallback(async () => {
    setIsModalOpen(true)
    await fetchTopics()
  }, [fetchTopics])

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false)
  }, [])

  const handleSelectTopic = useCallback(
    async (topicId: string) => {
      await startTutoring(topicId)
      setIsModalOpen(false)
    },
    [startTutoring]
  )

  return (
    <>
      <Button
        variant={variant}
        size={isCompact ? 'default' : 'lg'}
        onClick={handleOpenModal}
        className="gap-2"
        data-testid="teach-me-button"
      >
        <GraduationCap className={cn(isCompact ? 'h-4 w-4' : 'h-5 w-5')} />
        Teach Me
      </Button>

      <TopicSelectModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSelect={handleSelectTopic}
        topics={topics}
        isLoading={isLoadingTopics}
        analysisTitle={analysisTitle}
      />
    </>
  )
}
