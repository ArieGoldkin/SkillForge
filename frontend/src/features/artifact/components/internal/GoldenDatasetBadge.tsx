/**
 * GoldenDatasetBadge - Badge component for golden dataset content
 *
 * Displays a badge with tooltip when content is from the golden dataset.
 * Helps users distinguish example content from real analyzed content.
 */

import type * as React from 'react'

import { Badge } from '@shared/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@shared/components/ui/tooltip'

interface GoldenDatasetBadgeProps {
  /**
   * Name of the document from the golden dataset
   */
  documentName?: string
  /**
   * Optional custom badge text
   * @default "📚 Golden Dataset"
   */
  badgeText?: string
}

/**
 * GoldenDatasetBadge component
 *
 * @example
 * ```tsx
 * <GoldenDatasetBadge documentName="Chain Of Thought" />
 * ```
 */
export const GoldenDatasetBadge: React.FC<GoldenDatasetBadgeProps> = ({
  documentName,
  badgeText = '📚 Golden Dataset',
}) => {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="secondary"
            className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 cursor-help"
            data-testid="golden-dataset-badge"
          >
            {badgeText}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-sm">
            This is example content from SkillForge's curated dataset.
            {documentName && (
              <span className="block mt-1 font-medium">Document: {documentName}</span>
            )}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

GoldenDatasetBadge.displayName = 'GoldenDatasetBadge'
