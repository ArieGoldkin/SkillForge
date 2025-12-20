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

import type { AnalysisStatus } from '@app-types/api'

import { DEMO_CONSTANTS, COMPONENT_CONSTANTS } from '@/lib/constants'

import type { SkillFilters as SkillFiltersType } from '@features/library/components/SkillFilters'
import { SkillFilters } from '@features/library/components/SkillFilters'
import { SkillGridView } from '@features/library/components/SkillGridView'
import { SkillSearch } from '@features/library/components/SkillSearch'

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
    durationRange: [DEMO_CONSTANTS.DURATION_RANGE_MIN, DEMO_CONSTANTS.DURATION_RANGE_MAX],
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
            debounceMs={COMPONENT_CONSTANTS.SEARCH_DEBOUNCE_MS}
          />
        </div>

        {/* Filters & Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <h3 className="text-lg font-medium mb-3">SkillFilters</h3>
            <SkillFilters
              filters={filters}
              onChange={setFilters}
              availableTags={availableTags}
              availableStatuses={['complete', 'in-progress', 'failed'] satisfies AnalysisStatus[]}
            />
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
