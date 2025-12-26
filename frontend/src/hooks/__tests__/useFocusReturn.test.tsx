import { renderHook } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

import { useFocusReturn } from '../useFocusReturn'

describe('useFocusReturn', () => {
  let mockButton: HTMLButtonElement

  beforeEach(() => {
    // Create a mock button element
    mockButton = document.createElement('button')
    mockButton.textContent = 'Test Button'
    document.body.appendChild(mockButton)
  })

  afterEach(() => {
    // Only remove if still in DOM
    if (mockButton.parentNode) {
      document.body.removeChild(mockButton)
    }
  })

  it('should store the active element when modal opens', () => {
    // Focus the button before opening modal
    mockButton.focus()
    expect(document.activeElement).toBe(mockButton)

    // Render hook with isOpen=true
    renderHook(() => useFocusReturn(true))

    // The hook should have captured the button as the trigger element
    // We can't directly test the ref, but we can verify behavior in the next test
  })

  it('should return focus to trigger element when modal closes', () => {
    // Focus the button
    mockButton.focus()
    expect(document.activeElement).toBe(mockButton)

    // Open modal (captures current focus)
    const { rerender } = renderHook(({ isOpen }) => useFocusReturn(isOpen), {
      initialProps: { isOpen: true },
    })

    // Simulate focus moving to modal content
    const modalContent = document.createElement('div')
    document.body.appendChild(modalContent)
    modalContent.focus()

    // Close modal (should restore focus)
    rerender({ isOpen: false })

    // Focus should be returned to the original button
    expect(document.activeElement).toBe(mockButton)

    document.body.removeChild(modalContent)
  })

  it('should not restore focus if modal never opened', () => {
    mockButton.focus()

    // Render hook with isOpen=false from start
    const { rerender } = renderHook(({ isOpen }) => useFocusReturn(isOpen), {
      initialProps: { isOpen: false },
    })

    const otherElement = document.createElement('button')
    document.body.appendChild(otherElement)
    otherElement.focus()

    // "Close" modal (but it was never open)
    rerender({ isOpen: false })

    // Focus should not change
    expect(document.activeElement).toBe(otherElement)

    document.body.removeChild(otherElement)
  })

  it('should handle multiple open/close cycles', () => {
    // First cycle
    mockButton.focus()
    const { rerender } = renderHook(({ isOpen }) => useFocusReturn(isOpen), {
      initialProps: { isOpen: true },
    })

    const modalContent = document.createElement('div')
    document.body.appendChild(modalContent)
    modalContent.focus()

    rerender({ isOpen: false })
    expect(document.activeElement).toBe(mockButton)

    // Second cycle with different trigger
    const anotherButton = document.createElement('button')
    document.body.appendChild(anotherButton)
    anotherButton.focus()

    rerender({ isOpen: true })
    modalContent.focus()

    rerender({ isOpen: false })
    expect(document.activeElement).toBe(anotherButton)

    document.body.removeChild(modalContent)
    document.body.removeChild(anotherButton)
  })

  it('should handle case where trigger element is removed from DOM', () => {
    mockButton.focus()

    const { rerender } = renderHook(({ isOpen }) => useFocusReturn(isOpen), {
      initialProps: { isOpen: true },
    })

    // Create a spy before removing from DOM
    const focusSpy = vi.fn()
    mockButton.focus = focusSpy

    // Remove the button from DOM (after spy is set)
    document.body.removeChild(mockButton)

    // Close modal
    rerender({ isOpen: false })

    // Should still attempt to focus (even if element is detached)
    expect(focusSpy).toHaveBeenCalled()
  })
})
