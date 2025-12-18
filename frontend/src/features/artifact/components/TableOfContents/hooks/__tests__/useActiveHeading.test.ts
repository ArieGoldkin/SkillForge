/**
 * Tests for useActiveHeading hook
 */

import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { TocHeading } from '../../types'
import { getActiveHeading } from '../../utils'
import { useActiveHeading } from '../useActiveHeading'

// Mock the utils module
vi.mock('../../utils', () => ({
  getActiveHeading: vi.fn(),
}))

describe('useActiveHeading', () => {
  const mockHeadings: TocHeading[] = [
    {
      id: 'section-1',
      text: 'Section 1',
      level: 2,
      children: [
        {
          id: 'section-1-1',
          text: 'Section 1.1',
          level: 3,
        },
        {
          id: 'section-1-2',
          text: 'Section 1.2',
          level: 3,
        },
      ],
    },
    {
      id: 'section-2',
      text: 'Section 2',
      level: 2,
      children: [],
    },
  ]

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks()

    // Mock addEventListener and removeEventListener
    vi.spyOn(window, 'addEventListener')
    vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns null when headings array is empty', () => {
    vi.mocked(getActiveHeading).mockReturnValue(null)

    const { result } = renderHook(() => useActiveHeading([]))

    expect(result.current).toBe(null)
    expect(window.addEventListener).not.toHaveBeenCalled()
  })

  it('returns first heading when scroll position is at top', async () => {
    vi.mocked(getActiveHeading).mockReturnValue('section-1')

    const { result } = renderHook(() => useActiveHeading(mockHeadings))

    await waitFor(() => {
      expect(result.current).toBe('section-1')
    })

    expect(getActiveHeading).toHaveBeenCalledWith([
      'section-1',
      'section-1-1',
      'section-1-2',
      'section-2',
    ])
  })

  it('returns correct heading based on scroll position', async () => {
    vi.mocked(getActiveHeading).mockReturnValue('section-1-2')

    const { result } = renderHook(() => useActiveHeading(mockHeadings))

    await waitFor(() => {
      expect(result.current).toBe('section-1-2')
    })

    expect(getActiveHeading).toHaveBeenCalledWith([
      'section-1',
      'section-1-1',
      'section-1-2',
      'section-2',
    ])
  })

  it('updates active heading when scroll occurs', async () => {
    // Start with section-1 active
    vi.mocked(getActiveHeading).mockReturnValue('section-1')

    const { result } = renderHook(() => useActiveHeading(mockHeadings))

    await waitFor(() => {
      expect(result.current).toBe('section-1')
    })

    // Get the scroll event handler
    const scrollHandler = vi
      .mocked(window.addEventListener)
      .mock.calls.find((call) => call[0] === 'scroll')?.[1] as EventListener

    expect(scrollHandler).toBeDefined()

    // Simulate scroll and update active heading to section-2
    vi.mocked(getActiveHeading).mockReturnValue('section-2')

    await act(async () => {
      scrollHandler(new Event('scroll'))
    })

    await waitFor(() => {
      expect(result.current).toBe('section-2')
    })
  })

  it('handles DOM elements not found gracefully', async () => {
    // getActiveHeading returns null when elements are not found
    vi.mocked(getActiveHeading).mockReturnValue(null)

    const { result } = renderHook(() => useActiveHeading(mockHeadings))

    await waitFor(() => {
      expect(result.current).toBe(null)
    })
  })

  it('cleans up scroll listener on unmount', () => {
    const { unmount } = renderHook(() => useActiveHeading(mockHeadings))

    expect(window.addEventListener).toHaveBeenCalledWith('scroll', expect.any(Function), {
      passive: true,
    })

    unmount()

    expect(window.removeEventListener).toHaveBeenCalledWith('scroll', expect.any(Function))
  })

  it('flattens nested headings correctly', async () => {
    const nestedHeadings: TocHeading[] = [
      {
        id: 'parent-1',
        text: 'Parent 1',
        level: 2,
        children: [
          { id: 'child-1-1', text: 'Child 1.1', level: 3 },
          { id: 'child-1-2', text: 'Child 1.2', level: 3 },
        ],
      },
      {
        id: 'parent-2',
        text: 'Parent 2',
        level: 2,
        children: [{ id: 'child-2-1', text: 'Child 2.1', level: 3 }],
      },
    ]

    vi.mocked(getActiveHeading).mockReturnValue('child-1-1')

    renderHook(() => useActiveHeading(nestedHeadings))

    await waitFor(() => {
      expect(getActiveHeading).toHaveBeenCalledWith([
        'parent-1',
        'child-1-1',
        'child-1-2',
        'parent-2',
        'child-2-1',
      ])
    })
  })

  it('re-attaches scroll listener when headings change', async () => {
    const { rerender } = renderHook(({ headings }) => useActiveHeading(headings), {
      initialProps: { headings: mockHeadings },
    })

    // Initial render - should attach listener once
    expect(window.addEventListener).toHaveBeenCalledTimes(1)

    const newHeadings: TocHeading[] = [
      {
        id: 'new-section',
        text: 'New Section',
        level: 2,
        children: [],
      },
    ]

    // Clear the mock to count new calls
    vi.clearAllMocks()

    // Re-render with new headings
    rerender({ headings: newHeadings })

    // Should remove old listener and add new one
    await waitFor(() => {
      expect(window.removeEventListener).toHaveBeenCalledTimes(1)
      expect(window.addEventListener).toHaveBeenCalledTimes(1)
    })
  })

  it('calls handleScroll on initial mount', async () => {
    vi.mocked(getActiveHeading).mockReturnValue('section-1')

    const { result } = renderHook(() => useActiveHeading(mockHeadings))

    // getActiveHeading should be called immediately on mount
    await waitFor(() => {
      expect(getActiveHeading).toHaveBeenCalled()
      expect(result.current).toBe('section-1')
    })
  })

  it('handles headings with no children', async () => {
    const headingsWithoutChildren: TocHeading[] = [
      { id: 'section-1', text: 'Section 1', level: 2 },
      { id: 'section-2', text: 'Section 2', level: 2 },
    ]

    vi.mocked(getActiveHeading).mockReturnValue('section-1')

    renderHook(() => useActiveHeading(headingsWithoutChildren))

    await waitFor(() => {
      expect(getActiveHeading).toHaveBeenCalledWith(['section-1', 'section-2'])
    })
  })
})
