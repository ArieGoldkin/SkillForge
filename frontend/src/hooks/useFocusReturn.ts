import { useEffect, useRef } from 'react'

/**
 * useFocusReturn - Manages focus restoration when modal closes
 *
 * Captures the active element when modal opens and returns focus
 * to it when modal closes. Essential for WCAG 2.1 AA compliance.
 *
 * @param isOpen - Whether the modal is currently open
 *
 * @example
 * ```tsx
 * function MyModal({ isOpen, onClose }) {
 *   useFocusReturn(isOpen)
 *   return <Dialog open={isOpen}>...</Dialog>
 * }
 * ```
 */
export function useFocusReturn(isOpen: boolean): void {
  const triggerElementRef = useRef<HTMLElement | null>(null)

  // Store the active element when modal opens
  useEffect(() => {
    if (isOpen) {
      triggerElementRef.current = document.activeElement as HTMLElement
    }
  }, [isOpen])

  // Return focus to trigger element when modal closes
  useEffect(() => {
    if (!isOpen && triggerElementRef.current) {
      triggerElementRef.current.focus()
      triggerElementRef.current = null
    }
  }, [isOpen])
}
