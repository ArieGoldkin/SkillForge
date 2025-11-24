/**
 * LibraryTab - Showcase for library feature components
 *
 * Demonstrates:
 * - SkillSearch
 * - SkillFilters
 * - SkillGridView
 * - SkillCard
 */

import * as React from 'react'

import type { SkillFilters as SkillFiltersType } from '../library'
import { SkillFilters, SkillGridView, SkillSearch } from '../library'

import { availableTags, createSkills } from './showcase-data'

/**
 * LibraryTab component
 */
export const LibraryTab: React.FC = () => {
  // Use useState initializer to ensure factory is called only once
  const [skills] = React.useState(createSkills)
  const [filters, setFilters] = React.useState<SkillFiltersType>({
    difficulty: [],
    status: [],
    tags: [],
    durationRange: [0, 1000],
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">Library Components</h2>

      <div className="space-y-6">
        {/* Search */}
        <div>
          <h3 className="text-lg font-medium mb-3">SkillSearch</h3>
          <SkillSearch
            placeholder="Search skills..."
            onSearch={(query) => console.log('Search:', query)} // eslint-disable-line no-console -- Demo showcase only
            debounceMs={300}
          />
        </div>

        {/* Filters & Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <h3 className="text-lg font-medium mb-3">SkillFilters</h3>
            <SkillFilters filters={filters} onChange={setFilters} availableTags={availableTags} />
          </div>

          <div className="lg:col-span-3">
            <h3 className="text-lg font-medium mb-3">SkillGridView with SkillCards</h3>
            <SkillGridView
              skills={skills}
              onSelectSkill={(id) => console.log('Selected:', id)} // eslint-disable-line no-console -- Demo showcase only
            />
          </div>
        </div>
      </div>
    </div>
  )
}

LibraryTab.displayName = 'LibraryTab'
