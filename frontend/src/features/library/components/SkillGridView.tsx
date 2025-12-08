import type * as React from 'react'

import { BookOpen } from 'lucide-react'

import { Card } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

import { SkillCard, type SkillCardProps } from './SkillCard'

/** Stable IDs for loading skeleton placeholders */
const SKELETON_IDS = ['sk-1', 'sk-2', 'sk-3', 'sk-4', 'sk-5', 'sk-6'] as const

/**
 * Props for SkillGridView component
 */
export interface SkillGridViewProps {
  skills: SkillCardProps[]
  onSelectSkill: (id: string) => void
  onDeleteSkill?: (id: string) => void
  loading?: boolean
  emptyMessage?: string
  className?: string
}

/**
 * Loading skeleton for skill card
 */
const SkillCardSkeleton: React.FC = () => {
  return (
    <Card className="overflow-hidden">
      <div className="w-full h-48 bg-muted animate-pulse" />
      <div className="p-6 space-y-4">
        <div className="h-6 bg-muted rounded animate-pulse w-3/4" />
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-4 bg-muted rounded animate-pulse w-5/6" />
        </div>
        <div className="flex gap-2">
          <div className="h-6 bg-muted rounded animate-pulse w-20" />
          <div className="h-6 bg-muted rounded animate-pulse w-16" />
        </div>
      </div>
    </Card>
  )
}

/**
 * Empty state component
 */
const EmptyState: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-muted p-6 mb-4">
        <BookOpen className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">No Skills Found</h3>
      <p className="text-sm text-muted-foreground max-w-md">{message}</p>
    </div>
  )
}

/**
 * SkillGridView - Grid layout for SkillCards
 *
 * Displays skills in a responsive grid layout with loading states and empty state.
 * Automatically adjusts columns based on screen size.
 *
 * Grid breakpoints:
 * - Mobile: 1 column
 * - Tablet (md): 2 columns
 * - Desktop (lg): 3 columns
 *
 * @example
 * ```tsx
 * <SkillGridView
 *   skills={skillsData}
 *   onSelectSkill={(id) => router.push(`/skills/${id}`)}
 *   loading={isLoading}
 *   emptyMessage="Try adjusting your filters or search query"
 * />
 * ```
 */
export const SkillGridView: React.FC<SkillGridViewProps> = ({
  skills,
  onSelectSkill,
  onDeleteSkill,
  loading = false,
  emptyMessage = 'No skills found. Try adjusting your filters or search query.',
  className,
}) => {
  return (
    <div
      className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}
      role="list"
      aria-label="Skills grid"
    >
      {loading ? (
        // Loading skeletons
        SKELETON_IDS.map((id) => <SkillCardSkeleton key={id} />)
      ) : skills.length === 0 ? (
        // Empty state
        <EmptyState message={emptyMessage} />
      ) : (
        // Skill cards
        skills.map((skill) => (
          <SkillCard key={skill.id} {...skill} onSelect={onSelectSkill} onDelete={onDeleteSkill} />
        ))
      )}
    </div>
  )
}

SkillGridView.displayName = 'SkillGridView'
