/**
 * AnalysisTab - Showcase for analysis feature components
 *
 * Demonstrates:
 * - AnalysisProgressCard
 * - AnalysisStepList
 * - AgentActivityFeed
 */

import * as React from 'react'

import { DEMO_CONSTANTS } from '@/lib/constants'

import {
  AgentActivityFeed,
  AnalysisProgressCard,
  AnalysisStepList,
} from '@features/analysis/components'
import { MarkdownPreview } from '@features/artifact'

import { createAgentActivities, createAnalysisSteps } from './showcase-data'

// Sample markdown content for MarkdownPreview showcase
const sampleMarkdown = `# Implementation Guide: React API Integration

This guide covers best practices for integrating REST APIs in React applications.

## Key Concepts

- **Data Fetching**: Use \`useEffect\` or React Query for data fetching
- **Error Handling**: Always handle loading and error states
- **Type Safety**: Define TypeScript interfaces for API responses

## Code Example

\`\`\`typescript
interface User {
  id: number;
  name: string;
  email: string;
}

async function fetchUsers(): Promise<User[]> {
  const response = await fetch('/api/users');
  if (!response.ok) throw new Error('Failed to fetch');
  return response.json();
}
\`\`\`

## Best Practices

1. Centralize API logic in dedicated service files
2. Use environment variables for API base URLs
3. Implement request/response interceptors for auth

> **Note**: Always validate API responses at runtime using Zod or similar libraries.

| Feature | Recommended Tool |
|---------|-----------------|
| Data Fetching | React Query / SWR |
| State Management | Zustand / Jotai |
| Type Validation | Zod |
`

/**
 * AnalysisTab component
 */
export const AnalysisTab: React.FC = () => {
  // eslint-disable-line max-lines-per-function

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
            progress={DEMO_CONSTANTS.SAMPLE_PROGRESS_PERCENTAGE}
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
          <AgentActivityFeed
            activities={agentActivities}
            isLive={true}
            maxItems={DEMO_CONSTANTS.MAX_ACTIVITY_ITEMS}
          />
        </div>

        {/* Markdown Preview */}
        <div>
          <h3 className="text-lg font-medium mb-3">MarkdownPreview</h3>
          <MarkdownPreview
            content={sampleMarkdown}
            metadata={{
              topics: ['React', 'TypeScript', 'API Design'],
              complexity: 'intermediate',
              word_count: DEMO_CONSTANTS.SAMPLE_WORD_COUNT,
              agent_count: 5,
              avg_confidence: DEMO_CONSTANTS.SAMPLE_AVG_CONFIDENCE,
            }}
          />
        </div>
      </div>
    </div>
  )
}

AnalysisTab.displayName = 'AnalysisTab'
