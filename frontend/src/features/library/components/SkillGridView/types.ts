import type { SkillCardProps } from '../SkillCard'

/**
 * Props for SkillGridView component
 */
export interface SkillGridViewProps {
  skills: SkillCardProps[]
  onSelectSkill: (id: string) => void
  loading?: boolean
  emptyMessage?: string
  className?: string
  onLoadMore?: () => void
  canLoadMore?: boolean
  isLoadingMore?: boolean
}

/**
 * Props for VirtualizedGrid component
 */
export interface VirtualizedGridProps {
  skills: SkillCardProps[]
  onSelectSkill: (id: string) => void
  className?: string
}

/**
 * Props for VirtualizedRow component
 */
export interface VirtualizedRowProps {
  skills: SkillCardProps[]
  startIndex: number
  columnsPerRow: number
  onSelectSkill: (id: string) => void
}
