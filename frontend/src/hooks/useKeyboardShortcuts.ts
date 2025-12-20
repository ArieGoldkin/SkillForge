/**
 * Keyboard Shortcuts Hook
 *
 * WCAG 2.1.1 (Keyboard) & 2.1.4 (Character Key Shortcuts):
 * Provides configurable keyboard shortcuts for app-wide navigation.
 *
 * Features:
 * - Modifier key support (ctrl, shift, alt, meta)
 * - Prevents shortcuts when typing in inputs
 * - Cleanup on unmount
 * - TypeScript-safe shortcut definitions
 */

import { useCallback, useEffect, useMemo } from 'react'

/**
 * Keyboard shortcut definition
 */
export interface Shortcut {
  /** Key to trigger (e.g., 'k', 'Escape', 'ArrowDown') */
  key: string
  /** Require Ctrl/Cmd key */
  ctrl?: boolean
  /** Require Shift key */
  shift?: boolean
  /** Require Alt/Option key */
  alt?: boolean
  /** Require Meta (Cmd on Mac) key */
  meta?: boolean
  /** Action to execute */
  action: () => void
  /** Human-readable description for help dialog */
  description: string
  /** Prevent default browser behavior */
  preventDefault?: boolean
}

/**
 * Check if event target is an input element where shortcuts should be disabled
 */
function isInputElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false

  const tagName = target.tagName.toLowerCase()
  const isEditable = target.isContentEditable

  return tagName === 'input' || tagName === 'textarea' || tagName === 'select' || isEditable
}

/**
 * Check if a keyboard event matches a shortcut definition
 */
function matchesShortcut(event: KeyboardEvent, shortcut: Shortcut): boolean {
  // Key must match (case-insensitive for letters)
  const keyMatches =
    event.key.toLowerCase() === shortcut.key.toLowerCase() || event.key === shortcut.key

  if (!keyMatches) return false

  // Check modifier keys (use metaKey OR ctrlKey for cross-platform ctrl)
  const ctrlRequired = shortcut.ctrl ?? false
  const shiftRequired = shortcut.shift ?? false
  const altRequired = shortcut.alt ?? false
  const metaRequired = shortcut.meta ?? false

  // For ctrl shortcuts, accept either ctrlKey or metaKey (Cmd on Mac)
  const ctrlMatches = ctrlRequired
    ? event.ctrlKey || event.metaKey
    : !event.ctrlKey && !event.metaKey

  const shiftMatches = shiftRequired === event.shiftKey
  const altMatches = altRequired === event.altKey
  const metaMatches = metaRequired ? event.metaKey : true // Don't require non-meta

  return ctrlMatches && shiftMatches && altMatches && metaMatches
}

/**
 * Hook for registering keyboard shortcuts
 *
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   { key: 'k', ctrl: true, action: openSearch, description: 'Open search' },
 *   { key: 'Escape', action: closeModal, description: 'Close modal' },
 *   { key: '/', shift: true, action: showHelp, description: 'Show help' },
 * ])
 * ```
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[]): void {
  // Memoize shortcuts to prevent recreating handler on every render
  const shortcutList = useMemo(() => shortcuts, [shortcuts])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (isInputElement(event.target)) return

      for (const shortcut of shortcutList) {
        if (matchesShortcut(event, shortcut)) {
          if (shortcut.preventDefault !== false) {
            event.preventDefault()
          }
          shortcut.action()
          return // Only trigger first matching shortcut
        }
      }
    },
    [shortcutList]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

/**
 * Format shortcut for display (e.g., "⌘K" on Mac, "Ctrl+K" on Windows)
 */
export function formatShortcut(shortcut: Shortcut): string {
  const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.userAgent)
  const parts: string[] = []

  if (shortcut.ctrl) parts.push(isMac ? '⌘' : 'Ctrl')
  if (shortcut.shift) parts.push(isMac ? '⇧' : 'Shift')
  if (shortcut.alt) parts.push(isMac ? '⌥' : 'Alt')
  if (shortcut.meta) parts.push(isMac ? '⌘' : 'Win')

  // Format special keys
  const keyDisplay: Record<string, string> = {
    Escape: 'Esc',
    ArrowUp: '↑',
    ArrowDown: '↓',
    ArrowLeft: '←',
    ArrowRight: '→',
    Enter: '↵',
    ' ': 'Space',
  }

  parts.push(keyDisplay[shortcut.key] ?? shortcut.key.toUpperCase())

  return parts.join(isMac ? '' : '+')
}

export default useKeyboardShortcuts
