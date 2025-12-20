/**
 * Action buttons for AnalysisCompleteCard
 *
 * Issue #396: Removed prop drilling - GuideButton and TeachMeButton
 * now get their IDs directly from Zustand store.
 */

import { Eye } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

import { GuideButton } from './GuideButton'
import { TeachMeButton } from './TeachMeButton'

interface ActionButtonsProps {
  /** UI-only props */
  isCompact: boolean
  onPreview: () => void
}

export function ActionButtons({ isCompact, onPreview }: ActionButtonsProps) {
  return (
    <div className={cn('flex gap-3', isCompact && 'flex-col w-full')}>
      <Button
        variant="outline"
        size={isCompact ? 'default' : 'lg'}
        onClick={onPreview}
        className="gap-2"
      >
        <Eye className={cn(isCompact ? 'h-4 w-4' : 'h-5 w-5')} />
        Preview
      </Button>
      {/* TeachMeButton and GuideButton get IDs from store (Issue #396) */}
      <TeachMeButton isCompact={isCompact} />
      <GuideButton isCompact={isCompact} />
    </div>
  )
}
