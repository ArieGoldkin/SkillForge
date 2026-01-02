/**
 * Collapsible component for expandable content
 *
 * Based on Radix UI Collapsible primitive
 * Provides accessible expand/collapse functionality
 */

import * as React from 'react'

import { cn } from '@lib/utils'

interface CollapsibleContextValue {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const CollapsibleContext = React.createContext<CollapsibleContextValue | undefined>(undefined)

interface CollapsibleProps {
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
  className?: string
}

/**
 * Collapsible root component
 */
export function Collapsible({
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  children,
  className,
}: CollapsibleProps) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen)
  const open = openProp !== undefined ? openProp : internalOpen
  const setOpen = React.useCallback(
    (newOpen: boolean) => {
      if (openProp === undefined) {
        setInternalOpen(newOpen)
      }
      onOpenChange?.(newOpen)
    },
    [openProp, onOpenChange]
  )

  const contextValue = React.useMemo<CollapsibleContextValue>(
    () => ({
      open,
      onOpenChange: setOpen,
    }),
    [open, setOpen]
  )

  return (
    <CollapsibleContext.Provider value={contextValue}>
      <div className={cn('w-full', className)}>{children}</div>
    </CollapsibleContext.Provider>
  )
}

/**
 * Collapsible trigger button
 */
export function CollapsibleTrigger({
  asChild,
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean
}) {
  const context = React.useContext(CollapsibleContext)
  if (!context) {
    throw new Error('CollapsibleTrigger must be used within Collapsible')
  }

  const handleClick = () => {
    context.onOpenChange(!context.open)
  }

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...props,
      onClick: handleClick,
      'aria-expanded': context.open,
    } as React.HTMLAttributes<HTMLElement>)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-expanded={context.open}
      className={className}
      {...props}
    >
      {children}
    </button>
  )
}

/**
 * Collapsible content area
 */
export function CollapsibleContent({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const context = React.useContext(CollapsibleContext)
  if (!context) {
    throw new Error('CollapsibleContent must be used within Collapsible')
  }

  if (!context.open) {
    return null
  }

  return (
    <div className={cn('overflow-hidden', className)} {...props}>
      {children}
    </div>
  )
}
