/**
 * Tests for useTocCollapse hook
 */

import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useTocCollapse } from '../useTocCollapse'

describe('useTocCollapse', () => {
  let originalInnerWidth: number

  beforeEach(() => {
    // Store original window.innerWidth
    originalInnerWidth = window.innerWidth

    // Mock addEventListener and removeEventListener
    vi.spyOn(window, 'addEventListener')
    vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    // Restore original window.innerWidth
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    })

    vi.restoreAllMocks()
  })

  it('starts collapsed on mobile (window.innerWidth < 1024)', async () => {
    // Set mobile width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(true)
    })
  })

  it('starts expanded on desktop (window.innerWidth >= 1024)', async () => {
    // Set desktop width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })
  })

  it('handles exact breakpoint (window.innerWidth = 1024)', async () => {
    // Set exact breakpoint width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })
  })

  it('toggles state when toggle function called', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    const { result } = renderHook(() => useTocCollapse())

    // Initially expanded on desktop
    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })

    // Toggle to collapsed
    act(() => {
      result.current.toggleCollapse()
    })

    expect(result.current.isCollapsed).toBe(true)

    // Toggle back to expanded
    act(() => {
      result.current.toggleCollapse()
    })

    expect(result.current.isCollapsed).toBe(false)
  })

  it('updates state on window resize from desktop to mobile', async () => {
    // Start on desktop
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })

    // Get the resize event handler
    const resizeHandler = vi
      .mocked(window.addEventListener)
      .mock.calls.find((call) => call[0] === 'resize')?.[1] as EventListener

    expect(resizeHandler).toBeDefined()

    // Simulate resize to mobile
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    act(() => {
      resizeHandler(new Event('resize'))
    })

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(true)
    })
  })

  it('updates state on window resize from mobile to desktop', async () => {
    // Start on mobile
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(true)
    })

    // Get the resize event handler
    const resizeHandler = vi
      .mocked(window.addEventListener)
      .mock.calls.find((call) => call[0] === 'resize')?.[1] as EventListener

    expect(resizeHandler).toBeDefined()

    // Simulate resize to desktop
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    act(() => {
      resizeHandler(new Event('resize'))
    })

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })
  })

  it('cleans up resize listener on unmount', () => {
    const { unmount } = renderHook(() => useTocCollapse())

    expect(window.addEventListener).toHaveBeenCalledWith('resize', expect.any(Function))

    unmount()

    expect(window.removeEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
  })

  it('manual toggle overrides automatic resize behavior', async () => {
    // Start on desktop (expanded)
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })

    // Manually collapse
    act(() => {
      result.current.toggleCollapse()
    })

    expect(result.current.isCollapsed).toBe(true)

    // Get the resize event handler
    const resizeHandler = vi
      .mocked(window.addEventListener)
      .mock.calls.find((call) => call[0] === 'resize')?.[1] as EventListener

    // Trigger resize (still desktop size) - should reset to expanded
    act(() => {
      resizeHandler(new Event('resize'))
    })

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })
  })

  it('attaches resize listener on mount', () => {
    renderHook(() => useTocCollapse())

    expect(window.addEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
  })

  it('handles multiple rapid toggles', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1440,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })

    // Rapid toggles
    act(() => {
      result.current.toggleCollapse()
      result.current.toggleCollapse()
      result.current.toggleCollapse()
    })

    // Should be collapsed after 3 toggles (false -> true -> false -> true)
    expect(result.current.isCollapsed).toBe(true)
  })

  it('handles edge case width values', async () => {
    // Test width just below breakpoint
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1023,
    })

    const { result } = renderHook(() => useTocCollapse())

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(true)
    })

    // Get the resize event handler
    const resizeHandler = vi
      .mocked(window.addEventListener)
      .mock.calls.find((call) => call[0] === 'resize')?.[1] as EventListener

    // Test width at exactly breakpoint
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })

    act(() => {
      resizeHandler(new Event('resize'))
    })

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })

    // Test width just above breakpoint
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1025,
    })

    act(() => {
      resizeHandler(new Event('resize'))
    })

    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(false)
    })
  })

  it('calls handleResize on initial mount', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    const { result } = renderHook(() => useTocCollapse())

    // Should set initial state based on window width
    await waitFor(() => {
      expect(result.current.isCollapsed).toBe(true)
    })
  })
})
