import type { AgentActivity } from '../../hooks/useAnalysisProgress'
import { AgentActivityFeed } from './AgentActivityFeed'

interface ActivityColumnProps {
  activities: AgentActivity[]
  isLive?: boolean
}

export function ActivityColumn({ activities, isLive = false }: ActivityColumnProps) {
  return (
    <div className="lg:col-span-1">
      <AgentActivityFeed activities={activities} isLive={isLive} maxItems={15} />
    </div>
  )
}
