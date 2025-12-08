import type { SkillStatus } from './SkillCard'
import type { SkillFilters as SkillFiltersType } from './SkillFilters'
import { SkillFilters } from './SkillFilters'

interface FiltersSidebarProps {
  filters: SkillFiltersType
  onChange: (filters: SkillFiltersType) => void
  availableTags: string[]
  availableStatuses: SkillStatus[]
}

export function FiltersSidebar({
  filters,
  onChange,
  availableTags,
  availableStatuses,
}: FiltersSidebarProps) {
  return (
    <div className="lg:col-span-1">
      <SkillFilters
        filters={filters}
        onChange={onChange}
        availableTags={availableTags}
        availableStatuses={availableStatuses}
      />
    </div>
  )
}
