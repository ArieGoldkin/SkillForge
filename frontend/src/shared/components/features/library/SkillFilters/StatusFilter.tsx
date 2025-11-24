/**
 * StatusFilter - Status filter section
 */

import * as React from 'react'

import type { SkillStatus } from '../SkillCard'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for StatusFilter component
 */
export interface StatusFilterProps {
  selectedStatuses: SkillStatus[]
  onChange: (status: SkillStatus, checked: boolean) => void
}

/**
 * Available status values
 */
const statuses: SkillStatus[] = ['not-started', 'in-progress', 'completed']

/**
 * StatusFilter component
 *
 * Provides checkboxes for filtering by skill completion status.
 */
export const StatusFilter: React.FC<StatusFilterProps> = ({ selectedStatuses, onChange }) => {
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
