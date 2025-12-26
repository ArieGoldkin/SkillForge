import type * as React from 'react'

import { FileText, Users } from 'lucide-react'

import { COMPLEXITY_COLORS, COMPLEXITY_ICONS } from '../constants'
import type { ContentMetadata } from '../types'

interface MetadataStatsProps {
  complexity?: ContentMetadata['complexity']
  word_count?: number
  agent_count?: number
}

/**
 * MetadataStats - Display complexity, word count, and agent count
 */
export function MetadataStats({
  complexity,
  word_count,
  agent_count,
}: MetadataStatsProps): React.ReactNode {
  const ComplexityIcon = complexity ? COMPLEXITY_ICONS[complexity] : null
  const complexityColor = complexity ? COMPLEXITY_COLORS[complexity] : undefined

  return (
    <div className="flex items-center gap-4 text-sm text-muted-foreground">
      {complexity && ComplexityIcon && (
        <span className="flex items-center gap-1" style={{ color: complexityColor }}>
          <ComplexityIcon className="w-4 h-4" />
          <span className="capitalize font-medium">{complexity}</span>
        </span>
      )}

      {word_count !== undefined && (
        <span className="flex items-center gap-1">
          <FileText className="w-4 h-4" />
          <span>{word_count.toLocaleString()} words</span>
        </span>
      )}

      {agent_count !== undefined && (
        <span className="flex items-center gap-1">
          <Users className="w-4 h-4" />
          <span>{agent_count} agents</span>
        </span>
      )}
    </div>
  )
}

MetadataStats.displayName = 'MetadataStats'
