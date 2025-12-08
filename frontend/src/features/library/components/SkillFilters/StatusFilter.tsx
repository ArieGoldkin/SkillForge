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
export const StatusFilter: React.FC<StatusFilterProps> = ({
  selectedStatuses,
  availableStatuses,
  onChange,
}) => {
  return (
    <FilterSection title="Status">
      {availableStatuses.map((status) => (
        <CheckboxItem
          key={status}
          id={`status-${status}`}
          label={status.replace('-', ' ')}
          checked={selectedStatuses.includes(status)}
          onChange={(checked) => onChange(status, checked)}
        />
      ))}
    </FilterSection>
  )
}

StatusFilter.displayName = 'StatusFilter'
