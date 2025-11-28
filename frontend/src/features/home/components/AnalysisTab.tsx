/**
 * AnalysisTab - Showcase for analysis feature components
 *
 * Demonstrates:
 * - AnalysisProgressCard
 * - AnalysisStepList
 * - AgentActivityFeed
 */

import * as React from 'react'

import {
  AgentActivityFeed,
  AnalysisProgressCard,
  AnalysisStepList,
} from '@features/analysis/components'

import { createAgentActivities, createAnalysisSteps } from './showcase-data'

/**
 * AnalysisTab component
 */
export const AnalysisTab: React.FC = () => {
  // Use useState initializer to ensure Date.now() is called only once (React purity)
  const [analysisSteps] = React.useState(createAnalysisSteps)
  const [agentActivities] = React.useState(createAgentActivities)

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">Analysis Components</h2>

      <div className="space-y-6">
        {/* Progress Card */}
        <div>
          <h3 className="text-lg font-medium mb-3">AnalysisProgressCard</h3>
          <AnalysisProgressCard
            stage="analyzing"
            progress={60}
            currentStep="Multi-Agent Analysis"
            totalSteps={3}
            completedSteps={2}
            estimatedTimeRemaining="2-3 minutes"
          />
        </div>

        {/* Step List */}
        <div>
          <h3 className="text-lg font-medium mb-3">AnalysisStepList</h3>
          <AnalysisStepList steps={analysisSteps} />
        </div>

        {/* Activity Feed */}
        <div>
          <h3 className="text-lg font-medium mb-3">AgentActivityFeed</h3>
          <AgentActivityFeed activities={agentActivities} isLive={true} maxItems={10} />
        </div>
      </div>
    </div>
  )
}

AnalysisTab.displayName = 'AnalysisTab'
