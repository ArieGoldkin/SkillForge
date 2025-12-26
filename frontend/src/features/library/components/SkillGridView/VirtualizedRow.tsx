import type React from 'react'

import { SkillCard } from '../SkillCard'

import type { VirtualizedRowProps } from './types'

/**
 * VirtualizedRow - Renders a single row of skill cards
 *
 * Extracts the appropriate subset of skills for this row index
 * and renders them in a flex layout. Handles partial rows gracefully.
 *
 * @example
 * ```tsx
 * <VirtualizedRow
 *   skills={allSkills}
 *   startIndex={0}
 *   columnsPerRow={3}
 *   onSelectSkill={handleSelect}
 * />
 * ```
 */
export function VirtualizedRow({
  skills,
  startIndex,
  columnsPerRow,
  onSelectSkill,
}: VirtualizedRowProps): React.ReactNode {
  const rowSkills = skills.slice(startIndex, startIndex + columnsPerRow)

  return (
    <div className="flex gap-6 w-full">
      {rowSkills.map((skill) => (
        <div
          key={skill.id}
          className="flex-1 min-w-0"
          style={{
            maxWidth: `calc((100% - ${(columnsPerRow - 1) * 1.5}rem) / ${columnsPerRow})`,
          }}
        >
          <SkillCard {...skill} onSelect={onSelectSkill} />
        </div>
      ))}
      {/* Fill empty columns in partial rows */}
      {Array.from({ length: columnsPerRow - rowSkills.length }).map((_, idx) => (
        <div
          key={`empty-${startIndex + columnsPerRow + idx}`}
          className="flex-1 min-w-0"
          style={{
            maxWidth: `calc((100% - ${(columnsPerRow - 1) * 1.5}rem) / ${columnsPerRow})`,
          }}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}

VirtualizedRow.displayName = 'VirtualizedRow'
