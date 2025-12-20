import { useEffect, useRef } from 'react'

/**
 * Custom hook for managing focus when analysis completes
 * WCAG 2.4.3: Focus Order - Moves focus to completion card for screen readers
 */
export const useCompletionFocus = (isComplete: boolean) => {
  const completionRef = useRef<HTMLDivElement>(null)
  const hasAnnouncedRef = useRef(false)

  useEffect(() => {
    if (isComplete && completionRef.current && !hasAnnouncedRef.current) {
      // Focus the completion card for screen reader users
      completionRef.current.focus()
      hasAnnouncedRef.current = true
    }
  }, [isComplete])

  // Reset announcement flag when not complete
  useEffect(() => {
    if (!isComplete) {
      hasAnnouncedRef.current = false
    }
  }, [isComplete])

  return completionRef
}
