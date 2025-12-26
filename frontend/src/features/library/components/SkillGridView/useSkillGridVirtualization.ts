import { useEffect, useRef, useState } from 'react'

import { useVirtualizer } from '@tanstack/react-virtual'

/**
 * Calculate columns per row based on container width
 */
const getColumnsPerRow = (width: number): number => {
  if (width >= 1024) return 3 // lg breakpoint
  if (width >= 768) return 2 // md breakpoint
  return 1
}

/**
 * Custom hook for skill grid virtualization
 *
 * Provides row-based virtualization for a responsive grid layout.
 * Automatically adjusts columns per row based on container width.
 *
 * @param itemCount - Total number of items to virtualize
 * @returns Virtualization state and refs
 */
export function useSkillGridVirtualization(itemCount: number) {
  const parentRef = useRef<HTMLDivElement>(null)
  const [columnsPerRow, setColumnsPerRow] = useState(3)

  // Observe container width changes for responsive grid
  useEffect(() => {
    const container = parentRef.current
    if (!container) return

    const updateColumns = () => {
      const width = container.offsetWidth
      setColumnsPerRow(getColumnsPerRow(width))
    }

    // Initial calculation
    updateColumns()

    // Watch for resize
    const resizeObserver = new ResizeObserver(updateColumns)
    resizeObserver.observe(container)

    return () => resizeObserver.disconnect()
  }, [])

  const rowCount = Math.ceil(itemCount / columnsPerRow)

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual is safe to use
  const rowVirtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 280, // Approximate card height + gap
    overscan: 2, // Render 2 extra rows above/below viewport
  })

  return {
    parentRef,
    rowVirtualizer,
    rowCount,
    columnsPerRow,
  }
}
