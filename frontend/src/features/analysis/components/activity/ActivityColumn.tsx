import { memo } from 'react'

import type { AgentActivity } from '../../hooks/useAnalysisProgress'

import { AgentActivityFeed } from './AgentActivityFeed'

interface ActivityColumnProps {
  activities: AgentActivity[]
  isLive?: boolean
}

/**
 * ActivityColumn - Displays agent activity feed
 *
 * Wrapped with React.memo to prevent re-renders when parent re-renders
 * but activities and isLive haven't changed.
 */
export const ActivityColumn = memo(function ActivityColumn({
  activities,
  isLive = false,
}: ActivityColumnProps) {
  return (
    <div className="lg:col-span-1">
      <AgentActivityFeed activities={activities} isLive={isLive} maxItems={15} />
    </div>
  )
})
