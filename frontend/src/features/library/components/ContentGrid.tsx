import { SkillGridView } from "@/shared/components/features/library/SkillGridView";

import { LoadingGrid } from "./LoadingGrid";

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

interface ContentGridProps {
  isLoading: boolean;
  skills: Skill[];
  onSelectSkill: (id: string) => void;
}

export function ContentGrid({ isLoading, skills, onSelectSkill }: ContentGridProps) {
  if (isLoading) return <LoadingGrid />;

  return (
    <div className="lg:col-span-3">
      <SkillGridView skills={skills} onSelectSkill={onSelectSkill} />
    </div>
  );
}
