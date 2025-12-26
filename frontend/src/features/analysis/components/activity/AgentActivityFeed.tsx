import * as React from 'react'

import { Activity } from 'lucide-react'

import { COMPONENT_CONSTANTS } from '@/lib/constants'

import { Badge } from '@shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

/**
 * Individual agent activity entry
 *
 * @property id - Unique identifier for the activity
 * @property agentName - Name of the agent performing the action
 * @property action - Description of what the agent is doing
 * @property timestamp - When the activity occurred
 * @property metadata - Optional additional data about the activity
 */
export interface AgentActivity {
  id: string
  agentName: string
  action: string
  timestamp: Date
  metadata?: Record<string, unknown>
}

/**
 * Props for AgentActivityFeed component
 */
export interface AgentActivityFeedProps {
  activities: AgentActivity[]
  isLive?: boolean
  maxItems?: number
  className?: string
}

/**
 * Format timestamp to HH:MM:SS
 */
const formatTimestamp = (timestamp: Date): string => {
  return timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/**
 * Generate deterministic color for agent name
 */
const getAgentColor = (agentName: string): string => {
  // Simple hash function for consistent colors
  let hash = 0
  for (let i = 0; i < agentName.length; i++) {
    hash = agentName.charCodeAt(i) + ((hash << 5) - hash)
  }

  const colors = [
    'bg-chart-1', // Teal
    'bg-chart-2', // Purple
    'bg-chart-3', // Magenta
    'bg-chart-4', // Yellow-green
    'bg-chart-5', // Green
  ]

  return colors[Math.abs(hash) % colors.length]
}

/**
 * Individual activity log entry
 */
function ActivityEntry({
  activity,
  isNew,
}: {
  activity: AgentActivity
  isNew?: boolean
}): React.ReactNode {
  const agentInitial = activity.agentName.charAt(0).toUpperCase()
  const agentColor = getAgentColor(activity.agentName)

  return (
    <div
      className={cn(
        'group flex items-start gap-3 px-4 py-3 border-l-2 border-transparent transition-all hover:bg-accent/50 hover:border-l-primary',
        isNew && 'animate-in slide-in-from-right-2 duration-300'
      )}
    >
      {/* Agent badge */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white',
          agentColor
        )}
        title={activity.agentName}
      >
        {agentInitial}
      </div>

      {/* Activity content */}
      <div className="flex-1 space-y-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium truncate">{activity.agentName}</span>
          <span className="text-xs text-muted-foreground font-mono shrink-0">
            {formatTimestamp(activity.timestamp)}
          </span>
        </div>
        <p className="text-sm text-muted-foreground wrap-break-word">{activity.action}</p>
      </div>
    </div>
  )
}

/**
 * AgentActivityFeed - Real-time updates from LangGraph agents
 *
 * Displays a scrollable feed of agent activities in reverse chronological order.
 * Prepared for Server-Sent Events (SSE) integration in Sprint 2.
 * Shows live indicator when receiving real-time updates.
 *
 * @example
 * ```tsx
 * <AgentActivityFeed
 *   activities={[
 *     {
 *       id: '1',
 *       agentName: 'Tech Comparator',
 *       action: 'Comparing React Server Components vs traditional SSR',
 *       timestamp: new Date()
 *     },
 *     {
 *       id: '2',
 *       agentName: 'Security Auditor',
 *       action: 'Analyzing authentication patterns...',
 *       timestamp: new Date(Date.now() - 5000)
 *     }
 *   ]}
 *   isLive={true}
 *   maxItems={10}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Main component requires comprehensive JSX layout for feed UI (header, empty state, scrollable list, footer). Well-structured with extracted ActivityEntry sub-component. */
export function AgentActivityFeed({
  activities,
  isLive = false,
  maxItems = COMPONENT_CONSTANTS.MAX_ITEMS_DEFAULT,
  className,
}: AgentActivityFeedProps): React.ReactNode {
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [previousCount, setPreviousCount] = React.useState(activities.length)

  // Auto-scroll to newest activity when new items are added
  React.useEffect(() => {
    if (activities.length > previousCount && scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
    setPreviousCount(activities.length)
  }, [activities.length, previousCount])

  // Limit displayed items
  const displayedActivities = activities.slice(0, maxItems)
  const hasMore = activities.length > maxItems

  return (
    <Card className={cn('animate-in fade-in-50 duration-300', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Activity Log
          </CardTitle>
          {isLive && (
            <Badge variant="success" className="gap-1">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
              Live
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {displayedActivities.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Activity className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">Waiting for agent activity...</p>
          </div>
        ) : (
          <>
            <div
              ref={scrollRef}
              className="max-h-96 overflow-y-auto overscroll-contain"
              role="log"
              aria-live={isLive ? 'polite' : 'off'}
              aria-label="Agent activity feed"
            >
              {displayedActivities.map((activity, index) => (
                <ActivityEntry
                  key={activity.id}
                  activity={activity}
                  isNew={index === 0 && isLive}
                />
              ))}
            </div>
            {hasMore && (
              <div className="border-t px-4 py-3 text-center text-xs text-muted-foreground">
                Showing {maxItems} of {activities.length} activities
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

AgentActivityFeed.displayName = 'AgentActivityFeed'
