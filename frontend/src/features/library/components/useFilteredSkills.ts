import type { SkillFilters as SkillFiltersType } from "@/shared/components/features/library/SkillFilters";

interface Skill {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  duration: number;
  difficulty: "beginner" | "intermediate" | "advanced";
  tags: string[];
  progress: number;
  status: "not-started" | "in-progress" | "completed";
  onSelect: (id: string) => void;
}

export function useFilteredSkills(
  skills: Skill[],
  searchQuery: string,
  filters: SkillFiltersType
) {
  return skills.filter((skill) => {
    if (
      searchQuery &&
      !skill.title.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    if (
      filters.difficulty.length &&
      !filters.difficulty.includes(skill.difficulty)
    ) {
      return false;
    }
    if (filters.status.length && !filters.status.includes(skill.status)) {
      return false;
    }
    return true;
  });
}
