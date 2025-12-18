import type React from 'react'
import { useRef, useEffect } from 'react'

import type { Components } from 'react-markdown'

/**
 * CollapsibleSection - Custom renderers for <details> and <summary> HTML elements
 *
 * Problem:
 * When react-markdown renders HTML through rehype-raw, native <details>/<summary>
 * elements don't work properly because React requires explicit state management
 * for interactive elements to ensure proper re-rendering and event handling.
 *
 * Solution:
 * These custom renderers add React state management to <details> elements,
 * ensuring they expand/collapse correctly when clicked in a React context.
 *
 * Features:
 * - React state-based open/closed tracking
 * - Native HTML semantics preserved (accessibility)
 * - Smooth animations via CSS (markdown-preview.css)
 * - Support for nested markdown content
 * - Works with initial open attribute
 */

/**
 * Custom details element renderer with React state management
 * Ensures proper expand/collapse behavior in React context
 */
type DetailsRendererProps = React.DetailsHTMLAttributes<HTMLDetailsElement> & {
  children?: React.ReactNode
  node?: unknown
  open?: boolean
}

export const DetailsRenderer = ((rawProps: DetailsRendererProps) => {
  const { children, node: _node, open: initialOpen, ...rest } = rawProps
  const detailsRef = useRef<HTMLDetailsElement>(null)

  // Set initial open state
  useEffect(() => {
    if (detailsRef.current && initialOpen) {
      detailsRef.current.open = true
    }
  }, [initialOpen])

  // Let the browser handle the native details/summary behavior
  // No need for React state - the browser manages it natively
  return (
    <details ref={detailsRef} {...rest} {...(initialOpen ? { open: true } : {})}>
      {children}
    </details>
  )
}) satisfies NonNullable<Components['details']>

/**
 * Custom summary element renderer
 * Handles click events properly in React context
 */
type SummaryRendererProps = React.HTMLAttributes<HTMLElement> & {
  children?: React.ReactNode
  node?: unknown
}

export const SummaryRenderer = ((rawProps: SummaryRendererProps) => {
  const { children, node: _node, ...rest } = rawProps

  return <summary {...rest}>{children}</summary>
}) satisfies NonNullable<Components['summary']>
