/**
 * TagFilter - Tag filter section with scrollable list
 */

import type * as React from 'react'

import { CheckboxItem } from './CheckboxItem'
import { FilterSection } from './FilterSection'

/**
 * Props for TagFilter component
 */
export interface TagFilterProps {
  availableTags: string[]
  selectedTags: string[]
  onChange: (tag: string, checked: boolean) => void
}

/**
 * TagFilter component
 *
 * Provides scrollable list of tag checkboxes for filtering.
 * Supports large tag lists with max-height and overflow.
 */
export function TagFilter({
  availableTags,
  selectedTags,
  onChange,
}: TagFilterProps): React.ReactNode {
  if (availableTags.length === 0) {
    return null
  }

  return (
    <FilterSection title="Tags">
      <div className="max-h-48 overflow-y-auto space-y-1">
        {availableTags.map((tag) => (
          <CheckboxItem
            key={tag}
            id={`tag-${tag}`}
            label={tag}
            checked={selectedTags.includes(tag)}
            onChange={(checked) => onChange(tag, checked)}
          />
        ))}
      </div>
    </FilterSection>
  )
}

TagFilter.displayName = 'TagFilter'
