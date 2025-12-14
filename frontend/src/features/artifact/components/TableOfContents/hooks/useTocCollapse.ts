/**
 * Hook for managing TOC collapse state on mobile
 */

import { useEffect, useState } from 'react'

/**
 * Manage TOC collapse state with responsive behavior
 * - Collapsed by default on mobile (< 1024px)
 * - Expanded by default on desktop (>= 1024px)
 */
export function useTocCollapse() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  useEffect(() => {
    // Set initial state based on screen size
    const handleResize = () => {
      const isMobile = window.innerWidth < 1024
      setIsCollapsed(isMobile)
    }

    // Initial check
    handleResize()

    // Listen for resize events
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  const toggleCollapse = () => {
    setIsCollapsed((prev) => !prev)
  }

  return { isCollapsed, toggleCollapse }
}
