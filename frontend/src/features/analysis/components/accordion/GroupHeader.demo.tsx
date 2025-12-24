/**
 * Visual demo/test for GroupHeader component
 *
 * Shows all status states and responsive behavior examples.
 * Not imported in production - for development reference only.
 */

import { useState } from 'react'

import { FileText, Workflow, Shield, Code } from 'lucide-react'

import type { StageGroup, GroupStatus } from '@/features/analysis/types/accordion'

import { GroupHeader } from './GroupHeader'

// Example stage groups
const exampleGroups: StageGroup[] = [
  {
    id: 'core-workflow',
    label: 'Core Workflow',
    icon: Workflow,
    stages: ['extraction', 'chunking', 'embedding'],
    description: 'Essential pipeline stages',
  },
  {
    id: 'content-analysis',
    label: 'Content Analysis',
    icon: FileText,
    stages: ['content_analysis', 'technical_writer', 'security_auditor'],
    description: 'Content-based analysis agents',
  },
  {
    id: 'validation',
    label: 'Validation',
    icon: Shield,
    stages: ['tier2_fact_validation', 'tier2_source_credibility'],
    description: 'Tier 2 validation agents',
  },
  {
    id: 'quality',
    label: 'Quality',
    icon: Code,
    stages: ['quality_aggregation', 'quality_validation', 'quality_generation'],
    description: 'Quality and artifact generation',
  },
]

const statusOptions: GroupStatus[] = ['pending', 'in-progress', 'completed', 'failed', 'partial']

/**
 * Demo component showing all GroupHeader states
 */
/* eslint-disable max-lines-per-function, no-console -- Demo component with comprehensive examples for development reference */
export function GroupHeaderDemo() {
  const [expandedStates, setExpandedStates] = useState<Record<string, boolean>>({
    'core-workflow': true,
    'content-analysis': false,
    validation: false,
    quality: false,
  })

  const toggleGroup = (groupId: string) => {
    setExpandedStates((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }))
  }

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">GroupHeader Component Demo</h2>
        <p className="text-muted-foreground">
          Interactive examples showing all status states and responsive behavior
        </p>
      </div>

      {/* All Status States */}
      <div className="space-y-6">
        <h3 className="text-xl font-semibold">All Status States</h3>

        {statusOptions.map((status, index) => (
          <div key={status} className="space-y-2">
            <p className="text-sm text-muted-foreground">Status: {status}</p>
            <GroupHeader
              group={exampleGroups[index % exampleGroups.length]}
              status={status}
              progress={
                status === 'pending'
                  ? 0
                  : status === 'in-progress'
                    ? 45
                    : status === 'completed'
                      ? 100
                      : status === 'failed'
                        ? 33
                        : 67 // partial
              }
              isExpanded={expandedStates[exampleGroups[index % exampleGroups.length].id] ?? false}
              onToggle={() => toggleGroup(exampleGroups[index % exampleGroups.length].id)}
              stagesCompleted={
                status === 'pending'
                  ? 0
                  : status === 'in-progress'
                    ? 1
                    : status === 'completed'
                      ? 3
                      : status === 'failed'
                        ? 1
                        : 2 // partial
              }
              stagesTotal={3}
            />
          </div>
        ))}
      </div>

      {/* Interactive Example */}
      <div className="space-y-6">
        <h3 className="text-xl font-semibold">Interactive Accordion</h3>
        <p className="text-sm text-muted-foreground">
          Click each header to expand/collapse. Test keyboard navigation with Tab and Enter/Space.
        </p>

        <div className="border rounded-lg overflow-hidden">
          {exampleGroups.map((group, index) => (
            <GroupHeader
              key={group.id}
              group={group}
              status={
                index === 0
                  ? 'completed'
                  : index === 1
                    ? 'in-progress'
                    : index === 2
                      ? 'partial'
                      : 'pending'
              }
              progress={index === 0 ? 100 : index === 1 ? 66 : index === 2 ? 50 : 0}
              isExpanded={expandedStates[group.id] ?? false}
              onToggle={() => toggleGroup(group.id)}
              stagesCompleted={index === 0 ? 3 : index === 1 ? 2 : index === 2 ? 1 : 0}
              stagesTotal={3}
            />
          ))}
        </div>
      </div>

      {/* Touch Target Testing */}
      <div className="space-y-4">
        <h3 className="text-xl font-semibold">Touch Target Testing</h3>
        <p className="text-sm text-muted-foreground">
          Resize browser to test responsive touch targets:
          <br />
          Mobile (≤768px): 56px (h-14)
          <br />
          Tablet (768-1024px): 64px (h-16)
          <br />
          Desktop (≥1024px): 48px (h-12)
        </p>

        <div className="border rounded-lg overflow-hidden">
          <GroupHeader
            group={exampleGroups[0]}
            status="in-progress"
            progress={75}
            isExpanded={true}
            onToggle={() => console.log('Touch target test clicked')}
            stagesCompleted={2}
            stagesTotal={3}
          />
        </div>
      </div>
    </div>
  )
}
