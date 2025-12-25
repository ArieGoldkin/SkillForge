import type * as React from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@lib/utils'

/**
 * Base Skeleton Component with Shimmer Animation
 *
 * WCAG 2.1 AA Compliance:
 * - aria-hidden="true": Hidden from screen readers (decorative)
 * - role="presentation": Indicates no semantic meaning
 * - aria-busy implicitly indicated by parent loading state
 *
 * @example
 * <Skeleton className="h-4 w-full" />
 * <Skeleton className="h-12 w-12 rounded-full" />
 */
const skeletonVariants = cva(
  'animate-pulse bg-muted relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  {
    variants: {
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        md: 'rounded-md',
        lg: 'rounded-lg',
        full: 'rounded-full',
      },
    },
    defaultVariants: {
      rounded: 'md',
    },
  }
)

export interface SkeletonProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {}

const Skeleton = ({ className, rounded, ...props }: SkeletonProps) => {
  return (
    <div
      aria-hidden="true"
      role="presentation"
      className={cn(skeletonVariants({ rounded }), className)}
      {...props}
    />
  )
}

/**
 * Skeleton Text Component
 * Represents a single line of loading text with configurable width
 *
 * @example
 * <SkeletonText width="full" />
 * <SkeletonText width="3/4" />
 * <SkeletonText width="1/2" className="h-6" />
 */
const skeletonTextVariants = cva(
  'animate-pulse bg-muted h-4 relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  {
    variants: {
      width: {
        full: 'w-full',
        '3/4': 'w-3/4',
        '2/3': 'w-2/3',
        '1/2': 'w-1/2',
        '1/3': 'w-1/3',
        '1/4': 'w-1/4',
      },
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        md: 'rounded-md',
        lg: 'rounded-lg',
        full: 'rounded-full',
      },
    },
    defaultVariants: {
      width: 'full',
      rounded: 'md',
    },
  }
)

export interface SkeletonTextProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonTextVariants> {}

const SkeletonText = ({ className, width, rounded, ...props }: SkeletonTextProps) => {
  return (
    <div
      aria-hidden="true"
      role="presentation"
      className={cn(skeletonTextVariants({ width, rounded }), className)}
      {...props}
    />
  )
}

/**
 * Skeleton Circle Component
 * Circular skeleton for avatars, profile pictures, or round icons
 *
 * @example
 * <SkeletonCircle size="sm" />
 * <SkeletonCircle size="md" />
 * <SkeletonCircle size="lg" />
 * <SkeletonCircle className="h-24 w-24" />
 */
const skeletonCircleVariants = cva(
  'animate-pulse bg-muted rounded-full relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  {
    variants: {
      size: {
        xs: 'h-6 w-6',
        sm: 'h-8 w-8',
        md: 'h-10 w-10',
        lg: 'h-12 w-12',
        xl: 'h-16 w-16',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

export interface SkeletonCircleProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonCircleVariants> {}

const SkeletonCircle = ({ className, size, ...props }: SkeletonCircleProps) => {
  return (
    <div
      aria-hidden="true"
      role="presentation"
      className={cn(skeletonCircleVariants({ size }), className)}
      {...props}
    />
  )
}

/**
 * Skeleton Block Component
 * Rectangular content block for cards, images, or large content areas
 *
 * @example
 * <SkeletonBlock height="sm" />
 * <SkeletonBlock height="md" />
 * <SkeletonBlock height="lg" className="w-full" />
 * <SkeletonBlock className="h-48 w-full" />
 */
const skeletonBlockVariants = cva(
  'animate-pulse bg-muted w-full relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  {
    variants: {
      height: {
        xs: 'h-16',
        sm: 'h-24',
        md: 'h-32',
        lg: 'h-48',
        xl: 'h-64',
      },
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        md: 'rounded-md',
        lg: 'rounded-lg',
        xl: 'rounded-xl',
      },
    },
    defaultVariants: {
      height: 'md',
      rounded: 'md',
    },
  }
)

export interface SkeletonBlockProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonBlockVariants> {}

const SkeletonBlock = ({ className, height, rounded, ...props }: SkeletonBlockProps) => {
  return (
    <div
      aria-hidden="true"
      role="presentation"
      className={cn(skeletonBlockVariants({ height, rounded }), className)}
      {...props}
    />
  )
}

export { Skeleton, SkeletonText, SkeletonCircle, SkeletonBlock }
