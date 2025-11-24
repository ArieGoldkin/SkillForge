import { SkillFilters } from "@/shared/components/features/library/SkillFilters";
import type { SkillFilters as SkillFiltersType } from "@/shared/components/features/library/SkillFilters";

interface FiltersSidebarProps {
  filters: SkillFiltersType;
  onChange: (filters: SkillFiltersType) => void;
}

export function FiltersSidebar({ filters, onChange }: FiltersSidebarProps) {
  return (
    <div className="lg:col-span-1">
      <SkillFilters
        filters={filters}
        onChange={onChange}
        availableTags={[
          "article",
          "video",
          "repo",
          "complete",
          "analyzing",
        ]}
      />
    </div>
  );
}
