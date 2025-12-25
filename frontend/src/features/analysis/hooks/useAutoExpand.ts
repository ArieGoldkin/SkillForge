/* eslint-disable max-lines-per-function -- Complex hook with auto-expand/collapse logic, FIFO tracking, and effect cleanup requires extended implementation */
import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Configuration for breakpoint-aware expansion behavior
 */
export interface BreakpointConfig {
  /** Maximum number of simultaneously expanded groups */
  maxExpanded: number
  /** Delay in milliseconds before auto-collapsing old groups (0 = immediate) */
  autoCollapseDelay: number
}

/**
 * Return value from useAutoExpand hook
 */
export interface UseAutoExpandResult {
  /** Set of currently expanded group IDs */
  expandedGroups: Set<string>
  /** Replace the entire set of expanded groups */
  setExpandedGroups: (groups: Set<string>) => void
  /** Toggle a group's expansion state */
  toggleGroup: (groupId: string) => void
  /** Expand a specific group */
  expandGroup: (groupId: string) => void
  /** Collapse a specific group */
  collapseGroup: (groupId: string) => void
}

/**
 * Custom hook for automatic accordion expansion based on active stage.
 *
 * Features:
 * - Auto-expands the group containing the currently active stage
 * - Respects maximum expanded groups limit (breakpoint-aware)
 * - Auto-collapses oldest non-active groups when limit exceeded
 * - Supports configurable collapse delay
 * - Provides manual control functions for user interactions
 *
 * @param activeStageId - ID of the currently active stage, or null if none
 * @param stageToGroupMap - Map from stage ID to parent group ID
 * @param breakpointConfig - Configuration for expansion limits and timing
 * @returns Object with expanded state and control functions
 *
 * @example
 * ```tsx
 * const { expandedGroups, toggleGroup, expandGroup } = useAutoExpand(
 *   activeStageId,
 *   stageToGroupMap,
 *   { maxExpanded: 2, autoCollapseDelay: 300 }
 * );
 *
 * // Use in accordion
 * <Accordion.Item value={groupId} expanded={expandedGroups.has(groupId)}>
 *   <Accordion.Button onClick={() => toggleGroup(groupId)}>
 *     {groupName}
 *   </Accordion.Button>
 * </Accordion.Item>
 * ```
 */
export function useAutoExpand(
  activeStageId: string | null,
  stageToGroupMap: Map<string, string>,
  breakpointConfig: BreakpointConfig
): UseAutoExpandResult {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())

  // Track expansion order for FIFO collapse behavior
  const expansionOrderRef = useRef<string[]>([])

  // Track pending collapse timeouts
  const collapseTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Track the currently active group to prevent collapsing it
  const activeGroupRef = useRef<string | null>(null)

  /**
   * Expand a specific group and track its position in expansion order
   */
  const expandGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => {
      if (prev.has(groupId)) {
        return prev // Already expanded
      }

      const next = new Set(prev)
      next.add(groupId)

      // Add to expansion order if not already present
      if (!expansionOrderRef.current.includes(groupId)) {
        expansionOrderRef.current.push(groupId)
      }

      return next
    })

    // Cancel any pending collapse for this group
    const timeout = collapseTimeoutsRef.current.get(groupId)
    if (timeout) {
      clearTimeout(timeout)
      collapseTimeoutsRef.current.delete(groupId)
    }
  }, [])

  /**
   * Collapse a specific group and remove from expansion order
   */
  const collapseGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => {
      if (!prev.has(groupId)) {
        return prev // Already collapsed
      }

      const next = new Set(prev)
      next.delete(groupId)
      return next
    })

    // Remove from expansion order
    expansionOrderRef.current = expansionOrderRef.current.filter((id) => id !== groupId)

    // Cancel any pending collapse timeout
    const timeout = collapseTimeoutsRef.current.get(groupId)
    if (timeout) {
      clearTimeout(timeout)
      collapseTimeoutsRef.current.delete(groupId)
    }
  }, [])

  /**
   * Toggle a group's expansion state (for manual user interaction)
   */
  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)

      if (next.has(groupId)) {
        // Collapsing
        next.delete(groupId)
        expansionOrderRef.current = expansionOrderRef.current.filter((id) => id !== groupId)
      } else {
        // Expanding
        next.add(groupId)
        if (!expansionOrderRef.current.includes(groupId)) {
          expansionOrderRef.current.push(groupId)
        }
      }

      return next
    })
  }, [])

  /**
   * Collapse oldest non-active group with optional delay
   */
  const collapseOldestGroup = useCallback(
    (currentActiveGroup: string | null, delay: number) => {
      // Find oldest expanded group that is not the current active group
      const oldestGroup = expansionOrderRef.current.find(
        (groupId) => expandedGroups.has(groupId) && groupId !== currentActiveGroup
      )

      if (!oldestGroup) {
        return
      }

      if (delay === 0) {
        // Immediate collapse
        collapseGroup(oldestGroup)
      } else {
        // Delayed collapse
        const timeout = setTimeout(() => {
          collapseGroup(oldestGroup)
          collapseTimeoutsRef.current.delete(oldestGroup)
        }, delay)

        collapseTimeoutsRef.current.set(oldestGroup, timeout)
      }
    },
    [expandedGroups, collapseGroup]
  )

  /**
   * Auto-expand group containing active stage
   */
  useEffect(() => {
    if (!activeStageId) {
      activeGroupRef.current = null
      return
    }

    const activeGroup = stageToGroupMap.get(activeStageId)
    if (!activeGroup) {
      activeGroupRef.current = null
      return
    }

    activeGroupRef.current = activeGroup

    // Check if group is already expanded
    if (expandedGroups.has(activeGroup)) {
      return
    }

    // Expand the active group
    expandGroup(activeGroup)

    // Check if we need to collapse old groups
    const newExpandedCount = expandedGroups.size + 1
    if (newExpandedCount > breakpointConfig.maxExpanded) {
      const groupsToCollapse = newExpandedCount - breakpointConfig.maxExpanded

      for (let i = 0; i < groupsToCollapse; i++) {
        collapseOldestGroup(activeGroup, breakpointConfig.autoCollapseDelay)
      }
    }
  }, [
    activeStageId,
    stageToGroupMap,
    expandedGroups,
    breakpointConfig.maxExpanded,
    breakpointConfig.autoCollapseDelay,
    expandGroup,
    collapseOldestGroup,
  ])

  /**
   * Cleanup timeouts on unmount
   */
  useEffect(() => {
    // Copy ref value to local variable for cleanup (React hooks best practice)
    const timeoutsMap = collapseTimeoutsRef.current
    return () => {
      // Clear all pending timeouts
      for (const timeout of timeoutsMap.values()) {
        clearTimeout(timeout)
      }
      timeoutsMap.clear()
    }
  }, [])

  return {
    expandedGroups,
    setExpandedGroups,
    toggleGroup,
    expandGroup,
    collapseGroup,
  }
}
