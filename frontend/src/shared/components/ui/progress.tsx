import * as React from 'react'

import * as ProgressPrimitive from '@radix-ui/react-progress'

import { cn } from '@lib/utils'

/**
 * Progress bar color variants for different states
 */
export type ProgressVariant = 'default' | 'success' | 'warning' | 'error' | 'muted'

/**
 * Get indicator and background colors for each variant
 */
const getVariantClasses = (variant: ProgressVariant) => {
  const variants = {
    default: {
      background: 'bg-primary/20',
      indicator: 'bg-primary',
    },
    success: {
      background: 'bg-[oklch(0.6959_0.1491_162.4796)]/20',
      indicator: 'bg-[oklch(0.6959_0.1491_162.4796)]',
    },
    warning: {
      background: 'bg-[oklch(0.7686_0.1647_70.0804)]/20',
      indicator: 'bg-[oklch(0.7686_0.1647_70.0804)]',
    },
    error: {
      background: 'bg-destructive/20',
      indicator: 'bg-destructive',
    },
    muted: {
      background: 'bg-muted',
      indicator: 'bg-muted-foreground/50',
    },
  }
  return variants[variant]
}

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
 * <Progress value={50} variant="success" aria-valuetext="Halfway through analysis" />
 */
const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
    /** Human-readable progress description for screen readers */
    'aria-valuetext'?: string
    /** Visual variant for different states */
    variant?: ProgressVariant
  }
>(({ className, value, variant = 'default', 'aria-valuetext': ariaValueText, ...props }, ref) => {
  const currentValue = value || 0
  const defaultValueText = `${currentValue}% complete`
  const variantClasses = getVariantClasses(variant)

  return (
    <ProgressPrimitive.Root
      ref={ref}
      className={cn(
        'relative h-2 w-full overflow-hidden rounded-full',
        variantClasses.background,
        className
      )}
      aria-valuenow={currentValue}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuetext={ariaValueText || defaultValueText}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn('h-full w-full flex-1 transition-all', variantClasses.indicator)}
        style={{ transform: `translateX(-${100 - currentValue}%)` }}
      />
    </ProgressPrimitive.Root>
  )
})
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
