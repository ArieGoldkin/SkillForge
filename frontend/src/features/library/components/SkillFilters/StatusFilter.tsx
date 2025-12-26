/**
 * StatusFilter - Status filter section
 */

import type * as React from 'react'

import type { AnalysisStatus } from '@app-types/api'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for StatusFilter component
 */
export interface StatusFilterProps {
  selectedStatuses: AnalysisStatus[]
  availableStatuses: AnalysisStatus[]
  onChange: (status: AnalysisStatus, checked: boolean) => void
}

/**
 * StatusFilter component
 *
 * Provides checkboxes for filtering by skill completion status.
 */
export function StatusFilter({
  selectedStatuses,
  availableStatuses,
  onChange,
}: StatusFilterProps): React.ReactNode {
  const statuses = availableStatuses.length
    ? availableStatuses
    : (['complete', 'in-progress', 'failed'] as AnalysisStatus[])

  return (
    <FilterSection title="Status">
      {statuses.map((status) => (
        <CheckboxItem
          key={status}
          id={`status-${status === 'complete' ? 'completed' : status}`}
          label={status === 'complete' ? 'completed' : status.replace('-', ' ')}
          checked={selectedStatuses.includes(status)}
          onChange={(checked) => onChange(status, checked)}
          type="radio"
          name="status-filter"
        />
      ))}
    </FilterSection>
  )
}

StatusFilter.displayName = 'StatusFilter'
