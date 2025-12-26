/**
 * StatusFilter - Status filter section
 */

import type * as React from 'react'

import type { FilterStatus } from '@app-types/api'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for StatusFilter component
 */
export interface StatusFilterProps {
  selectedStatuses: FilterStatus[]
  availableStatuses: FilterStatus[]
  onChange: (status: FilterStatus, checked: boolean) => void
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
    : (['complete', 'running', 'failed'] as FilterStatus[])

  const statusLabels: Record<FilterStatus, string> = {
    complete: 'Completed',
    running: 'In Progress',
    pending: 'Pending',
    failed: 'Failed',
  }

  return (
    <FilterSection title="Status">
      {statuses.map((status) => (
        <CheckboxItem
          key={status}
          id={`status-${status}`}
          label={statusLabels[status]}
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
