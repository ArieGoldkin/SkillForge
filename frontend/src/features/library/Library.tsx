import { useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

import { mockAnalyzeAPI } from "@/services/mock.service";
import type { SkillFilters as SkillFiltersType } from "@/shared/components/features/library/SkillFilters";
import { SkillSearch } from "@/shared/components/features/library/SkillSearch";

import { ContentGrid } from "./components/ContentGrid";
import { FiltersSidebar } from "./components/FiltersSidebar";
import { LibraryHeader } from "./components/LibraryHeader";
import { useFilteredSkills } from "./components/useFilteredSkills";
import { useSkillsData } from "./components/useSkillsData";

export default function Library() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<SkillFiltersType>({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 1000],
  });

  const { data: analyses, isLoading } = useQuery({
    queryKey: ["analyses"],
    queryFn: () => mockAnalyzeAPI.listAnalyses(),
  });

  const skills = useSkillsData(analyses);
  const filteredSkills = useFilteredSkills(skills, searchQuery, filters);

  const handleSelectSkill = (id: string) => {
    navigate({ to: "/analyze/$id", params: { id } });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <LibraryHeader />
      <div className="mb-6">
        <SkillSearch
          onSearch={setSearchQuery}
          placeholder="Search analyses..."
        />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <FiltersSidebar filters={filters} onChange={setFilters} />
        <ContentGrid
          isLoading={isLoading}
          skills={filteredSkills}
          onSelectSkill={handleSelectSkill}
        />
      </div>
    </div>
  );
}
