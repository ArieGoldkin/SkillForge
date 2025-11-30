import type * as React from 'react'

import { cn } from '@lib/utils'

import type { MetadataHeaderProps } from '../types'

import { MetadataStats } from './MetadataStats'
import { TopicBadges } from './TopicBadges'

/**
 * MetadataHeader - Display analysis metadata with topics and stats
 *
 * Shows topic badges, complexity level, word count, and optional agent metrics.
 * Responsive design adapts to mobile viewports.
 *
 * @example
 * ```tsx
 * <MetadataHeader
 *   metadata={{
 *     topics: ['React', 'TypeScript'],
 *     complexity: 'advanced',
 *     word_count: 2500
 *   }}
 * />
 * ```
 */
export const MetadataHeader: React.FC<MetadataHeaderProps> = ({ metadata, className }) => {
  const { topics = [], complexity, word_count, agent_count } = metadata

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-4',
        'px-6 py-4',
        'bg-muted',
        'rounded-lg mb-6',
        className
      )}
    >
      <TopicBadges topics={topics} />

      <MetadataStats complexity={complexity} word_count={word_count} agent_count={agent_count} />
    </div>
  )
}

MetadataHeader.displayName = 'MetadataHeader'
