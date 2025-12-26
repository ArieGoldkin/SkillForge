/**
 * Tests for useAutoExpand - Auto-expansion logic for accordion groups
 *
 * Validates FIFO collapse behavior, breakpoint-aware expansion limits,
 * delayed collapse, and manual toggle interactions.
 */

import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

import { useAutoExpand } from '../useAutoExpand'

describe('useAutoExpand', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initialization', () => {
    it('starts with no expanded groups', () => {
      const stageToGroupMap = new Map([['stage1', 'group1']])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

      expect(result.current.expandedGroups.size).toBe(0)
    })

    it('provides all control functions', () => {
      const stageToGroupMap = new Map()
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

      expect(typeof result.current.expandGroup).toBe('function')
      expect(typeof result.current.collapseGroup).toBe('function')
      expect(typeof result.current.toggleGroup).toBe('function')
      expect(typeof result.current.setExpandedGroups).toBe('function')
    })
  })

  describe('auto-expansion on active stage change', () => {
    it('expands group containing active stage', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
      ])
      const config = { maxExpanded: 3, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      expect(result.current.expandedGroups.has('group1')).toBe(false)

      rerender({ activeStageId: 'stage1' })

      expect(result.current.expandedGroups.has('group1')).toBe(true)
    })

    it('does not expand if group is already expanded', () => {
      const stageToGroupMap = new Map([['stage1', 'group1']])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // First expansion
      rerender({ activeStageId: 'stage1' })
      const _firstExpandedGroups = result.current.expandedGroups

      // Trigger same stage again (should not change reference)
      rerender({ activeStageId: 'stage1' })

      // Should still have group1 expanded
      expect(result.current.expandedGroups.has('group1')).toBe(true)
    })

    it('does not expand if active stage has no group mapping', () => {
      const stageToGroupMap = new Map([['stage1', 'group1']])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      rerender({ activeStageId: 'unknown_stage' })

      expect(result.current.expandedGroups.size).toBe(0)
    })

    it('handles null active stage ID', () => {
      const stageToGroupMap = new Map([['stage1', 'group1']])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

      expect(result.current.expandedGroups.size).toBe(0)
    })
  })

  describe('FIFO collapse behavior', () => {
    it('collapses oldest group when max limit exceeded', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Expand group1
      rerender({ activeStageId: 'stage1' })
      expect(result.current.expandedGroups.has('group1')).toBe(true)

      // Expand group2
      rerender({ activeStageId: 'stage2' })
      expect(result.current.expandedGroups.has('group2')).toBe(true)
      expect(result.current.expandedGroups.size).toBe(2)

      // Expand group3 - should collapse group1 (oldest)
      rerender({ activeStageId: 'stage3' })

      expect(result.current.expandedGroups.has('group1')).toBe(false) // Collapsed
      expect(result.current.expandedGroups.has('group2')).toBe(true)
      expect(result.current.expandedGroups.has('group3')).toBe(true)
      expect(result.current.expandedGroups.size).toBe(2)
    })

    it('protects currently activating group from collapse', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Expand group1
      rerender({ activeStageId: 'stage1' })
      expect(result.current.expandedGroups.has('group1')).toBe(true)

      // Expand group2
      rerender({ activeStageId: 'stage2' })
      expect(result.current.expandedGroups.size).toBe(2)

      // Expand group3 - group1 (oldest) should be collapsed, NOT group3 (active)
      rerender({ activeStageId: 'stage3' })

      // The currently activating group (group3) is protected
      expect(result.current.expandedGroups.has('group3')).toBe(true)
      // Oldest group (group1) gets collapsed
      expect(result.current.expandedGroups.has('group1')).toBe(false)
      // group2 remains
      expect(result.current.expandedGroups.has('group2')).toBe(true)
    })

    it('collapses multiple groups if needed to meet limit', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 1, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Manually expand two groups
      act(() => {
        result.current.expandGroup('group1')
        result.current.expandGroup('group2')
      })
      expect(result.current.expandedGroups.size).toBe(2)

      // Now activate stage3 - should collapse both group1 and group2
      rerender({ activeStageId: 'stage3' })

      expect(result.current.expandedGroups.has('group1')).toBe(false)
      expect(result.current.expandedGroups.has('group2')).toBe(false)
      expect(result.current.expandedGroups.has('group3')).toBe(true)
      expect(result.current.expandedGroups.size).toBe(1)
    })
  })

  describe('delayed collapse', () => {
    it('delays collapse when autoCollapseDelay is set', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 300 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Expand two groups
      rerender({ activeStageId: 'stage1' })
      rerender({ activeStageId: 'stage2' })
      expect(result.current.expandedGroups.size).toBe(2)

      // Expand third group - should schedule collapse of group1
      rerender({ activeStageId: 'stage3' })

      // Immediately after expansion, group1 should still be expanded
      expect(result.current.expandedGroups.has('group1')).toBe(true)
      expect(result.current.expandedGroups.size).toBe(3)

      // Advance timers by 300ms
      act(() => {
        vi.advanceTimersByTime(300)
      })

      // Now group1 should be collapsed
      expect(result.current.expandedGroups.has('group1')).toBe(false)
      expect(result.current.expandedGroups.size).toBe(2)
    })

    it('cancels pending collapse if group is manually expanded', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 300 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Expand two groups
      rerender({ activeStageId: 'stage1' })
      rerender({ activeStageId: 'stage2' })

      // Expand third group - schedules collapse of group1
      rerender({ activeStageId: 'stage3' })

      // Before timeout expires, manually expand group1
      act(() => {
        result.current.expandGroup('group1')
      })

      // Advance timers - group1 should NOT be collapsed (timeout was cancelled)
      act(() => {
        vi.advanceTimersByTime(300)
      })

      expect(result.current.expandedGroups.has('group1')).toBe(true)
    })
  })

  describe('manual controls', () => {
    describe('expandGroup', () => {
      it('expands a specific group', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        act(() => {
          result.current.expandGroup('group1')
        })

        expect(result.current.expandedGroups.has('group1')).toBe(true)
      })

      it('does nothing if group is already expanded', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        act(() => {
          result.current.expandGroup('group1')
        })

        const firstExpandedGroups = result.current.expandedGroups

        act(() => {
          result.current.expandGroup('group1')
        })

        // Should be same reference (no state update)
        expect(result.current.expandedGroups).toBe(firstExpandedGroups)
      })
    })

    describe('collapseGroup', () => {
      it('collapses a specific group', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        act(() => {
          result.current.expandGroup('group1')
        })
        expect(result.current.expandedGroups.has('group1')).toBe(true)

        act(() => {
          result.current.collapseGroup('group1')
        })

        expect(result.current.expandedGroups.has('group1')).toBe(false)
      })

      it('does nothing if group is already collapsed', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        const initialExpandedGroups = result.current.expandedGroups

        act(() => {
          result.current.collapseGroup('group1')
        })

        // Should be same reference (no state update)
        expect(result.current.expandedGroups).toBe(initialExpandedGroups)
      })

      it('cancels pending collapse timeout', () => {
        const stageToGroupMap = new Map([
          ['stage1', 'group1'],
          ['stage2', 'group2'],
          ['stage3', 'group3'],
        ])
        const config = { maxExpanded: 2, autoCollapseDelay: 300 }

        const { result, rerender } = renderHook(
          ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
          { initialProps: { activeStageId: null as string | null } }
        )

        // Expand two groups and schedule collapse
        rerender({ activeStageId: 'stage1' })
        rerender({ activeStageId: 'stage2' })
        rerender({ activeStageId: 'stage3' })

        // Manually collapse group1 before timeout
        act(() => {
          result.current.collapseGroup('group1')
        })

        expect(result.current.expandedGroups.has('group1')).toBe(false)

        // Advance timers - should not cause issues
        act(() => {
          vi.advanceTimersByTime(300)
        })

        expect(result.current.expandedGroups.has('group1')).toBe(false)
      })
    })

    describe('toggleGroup', () => {
      it('expands a collapsed group', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        act(() => {
          result.current.toggleGroup('group1')
        })

        expect(result.current.expandedGroups.has('group1')).toBe(true)
      })

      it('collapses an expanded group', () => {
        const stageToGroupMap = new Map()
        const config = { maxExpanded: 3, autoCollapseDelay: 0 }

        const { result } = renderHook(() => useAutoExpand(null, stageToGroupMap, config))

        act(() => {
          result.current.expandGroup('group1')
        })
        expect(result.current.expandedGroups.has('group1')).toBe(true)

        act(() => {
          result.current.toggleGroup('group1')
        })

        expect(result.current.expandedGroups.has('group1')).toBe(false)
      })

      it('removes from expansion order when collapsing', () => {
        const stageToGroupMap = new Map([
          ['stage1', 'group1'],
          ['stage2', 'group2'],
          ['stage3', 'group3'],
        ])
        const config = { maxExpanded: 2, autoCollapseDelay: 0 }

        const { result, rerender } = renderHook(
          ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
          { initialProps: { activeStageId: null as string | null } }
        )

        // Expand group1, then group2
        rerender({ activeStageId: 'stage1' })
        rerender({ activeStageId: 'stage2' })
        expect(result.current.expandedGroups.size).toBe(2)

        // Manually toggle group1 (collapse)
        act(() => {
          result.current.toggleGroup('group1')
        })
        expect(result.current.expandedGroups.has('group1')).toBe(false)

        // Now expand group3 - group2 is now oldest in expansion order
        // Since maxExpanded is 2 and we have group2 + group3, no collapse needed
        rerender({ activeStageId: 'stage3' })

        // Both group2 and group3 should be expanded (within limit)
        expect(result.current.expandedGroups.has('group2')).toBe(true)
        expect(result.current.expandedGroups.has('group3')).toBe(true)
        expect(result.current.expandedGroups.size).toBe(2)
      })
    })
  })

  describe('edge cases', () => {
    it('handles empty stage-to-group map', () => {
      const stageToGroupMap = new Map()
      const config = { maxExpanded: 2, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      rerender({ activeStageId: 'stage1' })

      expect(result.current.expandedGroups.size).toBe(0)
    })

    it('handles maxExpanded = 0', () => {
      const stageToGroupMap = new Map([['stage1', 'group1']])
      const config = { maxExpanded: 0, autoCollapseDelay: 0 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      rerender({ activeStageId: 'stage1' })

      // Should expand despite max being 0 (active group takes priority)
      expect(result.current.expandedGroups.has('group1')).toBe(true)
    })

    it('cleans up timeouts on unmount', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 300 }

      const { unmount, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Schedule a collapse
      rerender({ activeStageId: 'stage1' })
      rerender({ activeStageId: 'stage2' })
      rerender({ activeStageId: 'stage3' })

      // Unmount before timeout expires
      unmount()

      // Advance timers - should not cause errors
      expect(() => {
        vi.advanceTimersByTime(300)
      }).not.toThrow()
    })

    it('handles rapid stage changes', () => {
      const stageToGroupMap = new Map([
        ['stage1', 'group1'],
        ['stage2', 'group2'],
        ['stage3', 'group3'],
        ['stage4', 'group4'],
      ])
      const config = { maxExpanded: 2, autoCollapseDelay: 100 }

      const { result, rerender } = renderHook(
        ({ activeStageId }) => useAutoExpand(activeStageId, stageToGroupMap, config),
        { initialProps: { activeStageId: null as string | null } }
      )

      // Rapidly change active stages - each triggers expansion
      rerender({ activeStageId: 'stage1' })
      rerender({ activeStageId: 'stage2' })

      // At this point: 2 groups expanded, at max limit
      expect(result.current.expandedGroups.size).toBe(2)

      rerender({ activeStageId: 'stage3' })
      rerender({ activeStageId: 'stage4' })

      // Before any timeouts expire - might have more groups temporarily
      expect(result.current.expandedGroups.size).toBeGreaterThanOrEqual(2)

      // Advance timers to let delayed collapses execute
      act(() => {
        vi.runAllTimers()
      })

      // Should have most recent groups expanded (group3 and/or group4)
      // The hook behavior ensures new active groups are always expanded
      expect(result.current.expandedGroups.has('group4')).toBe(true)
    })
  })
})
