/**
 * DurationFilter - Duration range filter section
 */

import type * as React from 'react'

import { FilterSection } from './FilterSection'

/**
 * DurationFilter component
 *
 * Placeholder for duration range filtering.
 * Currently displays a "coming soon" message.
 */
export function DurationFilter(): React.ReactNode {
  return (
    <FilterSection title="Duration">
      <div className="space-y-2 px-3 py-2">
        <div className="text-xs text-muted-foreground">Duration filtering coming soon</div>
      </div>
    </FilterSection>
  )
}

DurationFilter.displayName = 'DurationFilter'
