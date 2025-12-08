/**
 * StatusFilter - Status filter section
 */

import type * as React from 'react'

import type { SkillStatus } from '../SkillCard'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for StatusFilter component
 */
export interface StatusFilterProps {
  selectedStatuses: SkillStatus[]
  availableStatuses: SkillStatus[]
  onChange: (status: SkillStatus, checked: boolean) => void
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
  const statuses = availableStatuses.length
    ? availableStatuses
    : (['completed', 'in-progress', 'failed'] as SkillStatus[])

  return (
    <FilterSection title="Status">
      {statuses.map((status) => (
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
