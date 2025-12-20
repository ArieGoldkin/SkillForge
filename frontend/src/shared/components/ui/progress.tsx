import * as React from 'react'

import * as ProgressPrimitive from '@radix-ui/react-progress'

import { cn } from '@lib/utils'

/**
 * Accessible Progress Bar Component
 *
 * WCAG 2.1 AA Compliance:
 * - aria-valuenow: Current progress value (0-100)
 * - aria-valuemin: Minimum value (always 0)
 * - aria-valuemax: Maximum value (always 100)
 * - aria-valuetext: Human-readable description (optional, defaults to "{value}% complete")
 *
 * @example
 * <Progress value={75} aria-label="Upload progress" />
 * <Progress value={50} aria-valuetext="Halfway through analysis" />
 */
const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
    /** Human-readable progress description for screen readers */
    'aria-valuetext'?: string
  }
>(({ className, value, 'aria-valuetext': ariaValueText, ...props }, ref) => {
  const currentValue = value || 0
  const defaultValueText = `${currentValue}% complete`

  return (
    <ProgressPrimitive.Root
      ref={ref}
      className={cn('relative h-2 w-full overflow-hidden rounded-full bg-primary/20', className)}
      aria-valuenow={currentValue}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuetext={ariaValueText || defaultValueText}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className="h-full w-full flex-1 bg-primary transition-all"
        style={{ transform: `translateX(-${100 - currentValue}%)` }}
      />
    </ProgressPrimitive.Root>
  )
})
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
