/**
 * Action buttons for AnalysisCompleteCard
 */

import { Eye } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

import { GuideButton } from './GuideButton'
import { TeachMeButton } from './TeachMeButton'

interface ActionButtonsProps {
  artifactId: string
  analysisId?: string
  analysisTitle?: string
  isCompact: boolean
  onPreview: () => void
}

export function ActionButtons({
  artifactId,
  analysisId,
  analysisTitle,
  isCompact,
  onPreview,
}: ActionButtonsProps) {
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
      {analysisId && (
        <TeachMeButton
          analysisId={analysisId}
          analysisTitle={analysisTitle}
          isCompact={isCompact}
        />
      )}
      <GuideButton artifactId={artifactId} analysisId={analysisId} isCompact={isCompact} />
    </div>
  )
}
