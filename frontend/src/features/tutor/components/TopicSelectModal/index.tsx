/**
 * TopicSelectModal - Modal for selecting tutoring topic (Issue #114)
 */

import { useState } from 'react'

import { ArrowRight, GraduationCap, Info } from 'lucide-react'

import { useFocusReturn } from '@/hooks'

import { Button } from '@shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@shared/components/ui/dialog'

import { TopicContent } from './TopicContent'
import type { TopicSelectModalProps } from './types'

export function TopicSelectModal(props: TopicSelectModalProps) {
  const { isOpen, onClose, onSelect, topics, isLoading = false, analysisTitle } = props
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)

  // WCAG 2.1 AA: Return focus to trigger element when modal closes
  useFocusReturn(isOpen)

  const handleClose = () => {
    setSelectedTopicId(null)
    onClose()
  }

  const description = analysisTitle
    ? `Select a topic from "${analysisTitle}" to learn:`
    : 'Select a topic to learn:'

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            Start Tutoring Session
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <TopicContent
            isLoading={isLoading}
            topics={topics}
            selectedId={selectedTopicId}
            onSelect={setSelectedTopicId}
          />
        </div>

        <div className="flex items-start gap-2 rounded-lg bg-muted/50 p-3 text-sm">
          <Info className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-muted-foreground">Learn through Socratic dialogue.</p>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={() => selectedTopicId && onSelect(selectedTopicId)}
            disabled={!selectedTopicId || isLoading}
            className="gap-2"
          >
            Start Learning
            <ArrowRight className="h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export type { TopicSelectModalProps, TutoringTopic } from './types'
