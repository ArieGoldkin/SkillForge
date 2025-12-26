import type React from 'react'

import { cn } from '@lib/utils'

import type { VirtualizedGridProps } from './types'
import { useSkillGridVirtualization } from './useSkillGridVirtualization'
import { VirtualizedRow } from './VirtualizedRow'

/**
 * VirtualizedGrid - Virtualized grid container for skill cards
 *
 * Uses @tanstack/react-virtual for efficient row-based virtualization.
 * Only renders rows visible in the viewport plus a small overscan buffer.
 *
 * Features:
 * - Responsive grid (1/2/3 columns based on breakpoints)
 * - Row-based virtualization for large lists
 * - Automatic resize handling
 * - Accessibility support
 *
 * @example
 * ```tsx
 * <VirtualizedGrid
 *   skills={skills}
 *   onSelectSkill={handleSelect}
 *   className="custom-styles"
 * />
 * ```
 */
export function VirtualizedGrid({
  skills,
  onSelectSkill,
  className,
}: VirtualizedGridProps): React.ReactNode {
  const { parentRef, rowVirtualizer, columnsPerRow } = useSkillGridVirtualization(skills.length)

  const virtualItems = rowVirtualizer.getVirtualItems()

  return (
    <div
      ref={parentRef}
      className={cn('overflow-auto', className)}
      role="list"
      aria-label="Skills grid"
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map((virtualRow) => {
          const startIndex = virtualRow.index * columnsPerRow

          return (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              ref={rowVirtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <VirtualizedRow
                skills={skills}
                startIndex={startIndex}
                columnsPerRow={columnsPerRow}
                onSelectSkill={onSelectSkill}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

VirtualizedGrid.displayName = 'VirtualizedGrid'
