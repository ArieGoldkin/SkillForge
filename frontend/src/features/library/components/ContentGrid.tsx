import { LoadingGrid } from './LoadingGrid'
import type { SkillStatus } from './SkillCard'
import { SkillGridView } from './SkillGridView'

interface Skill {
  id: string
  title: string
  description: string
  thumbnail: string
  duration: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  tags: string[]
  progress?: number
  status: SkillStatus
  onSelect: (id: string) => void
}

interface ContentGridProps {
  isLoading: boolean
  skills: Skill[]
  onSelectSkill: (id: string) => void
  onLoadMore?: () => void
  isLoadingMore?: boolean
  canLoadMore?: boolean
}

export function ContentGrid({
  isLoading,
  skills,
  onSelectSkill,
  onLoadMore,
  isLoadingMore = false,
  canLoadMore = false,
}: ContentGridProps) {
  if (isLoading) return <LoadingGrid />

  return (
    <div className="lg:col-span-3">
      <SkillGridView
        skills={skills}
        onSelectSkill={onSelectSkill}
        onLoadMore={onLoadMore}
        canLoadMore={canLoadMore}
        isLoadingMore={isLoadingMore}
      />
    </div>
  )
}
