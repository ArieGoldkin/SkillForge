/**
 * Action buttons for annotation queue items.
 */

import { Link } from '@tanstack/react-router'
import { CheckCircle, ExternalLink } from 'lucide-react'

import { Button } from '@shared/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@shared/components/ui/tooltip'

interface QueueItemActionsProps {
  queueId: number
  artifactId: string
  status: string
  onMarkReviewed: (queueId: number) => void
  isMarkingReviewed: boolean
}

export function QueueItemActions({
  queueId,
  artifactId,
  status,
  onMarkReviewed,
  isMarkingReviewed,
}: QueueItemActionsProps) {
  const isReviewed = status === 'reviewed'

  return (
    <div className="flex items-center gap-2">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="sm" asChild>
              <Link
                to="/artifact/$artifactId"
                params={{ artifactId }}
                className="flex items-center gap-1"
              >
                <ExternalLink className="h-4 w-4" />
                <span className="sr-only md:not-sr-only">View</span>
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent>View artifact</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant={isReviewed ? 'secondary' : 'default'}
              size="sm"
              onClick={() => onMarkReviewed(queueId)}
              disabled={isReviewed || isMarkingReviewed}
              className="flex items-center gap-1"
            >
              <CheckCircle className="h-4 w-4" />
              <span className="sr-only md:not-sr-only">
                {isReviewed ? 'Reviewed' : 'Mark Reviewed'}
              </span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isReviewed ? 'Already reviewed' : 'Mark as reviewed'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}
