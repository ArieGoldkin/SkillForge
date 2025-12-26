import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Skeleton, SkeletonText, SkeletonCircle, SkeletonBlock } from '../skeleton'

/**
 * @unit Skeleton Component Tests
 *
 * Comprehensive test suite for skeleton loading components including:
 * - Base Skeleton component
 * - SkeletonText with configurable width
 * - SkeletonCircle with size variants
 * - SkeletonBlock with height/width props
 *
 * Tests cover:
 * 1. Rendering without crashes
 * 2. Accessibility (aria-hidden, role="presentation")
 * 3. Styling (bg-muted, animation classes)
 * 4. Variant behavior (size, width, height, rounded)
 * 5. Custom className merging
 */
describe('Skeleton Components', () => {
  describe('Skeleton (Base Component)', () => {
    it('renders without crashing @unit', () => {
      const { container } = render(<Skeleton />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders with default classes @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('has aria-hidden="true" for accessibility @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('aria-hidden', 'true')
    })

    it('has role="presentation" for accessibility @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('role', 'presentation')
    })

    it('merges custom className properly @unit', () => {
      const { container } = render(<Skeleton className="custom-class h-12 w-12" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('custom-class')
      expect(skeleton).toHaveClass('h-12')
      expect(skeleton).toHaveClass('w-12')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('applies shimmer animation classes @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      // Check for shimmer-related classes
      expect(skeleton.className).toContain('before:')
      expect(skeleton.className).toContain('animate-shimmer')
    })

    it('applies rounded variant - none @unit', () => {
      const { container } = render(<Skeleton rounded="none" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-none')
    })

    it('applies rounded variant - sm @unit', () => {
      const { container } = render(<Skeleton rounded="sm" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-sm')
    })

    it('applies rounded variant - md (default) @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-md')
    })

    it('applies rounded variant - lg @unit', () => {
      const { container } = render(<Skeleton rounded="lg" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-lg')
    })

    it('applies rounded variant - full @unit', () => {
      const { container } = render(<Skeleton rounded="full" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-full')
    })

    it('accepts and applies data-testid @unit', () => {
      render(<Skeleton data-testid="custom-skeleton" />)
      expect(screen.getByTestId('custom-skeleton')).toBeInTheDocument()
    })
  })

  describe('SkeletonText', () => {
    it('renders without crashing @unit', () => {
      const { container } = render(<SkeletonText />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders with default full width @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-full')
    })

    it('renders with configurable width - 3/4 @unit', () => {
      const { container } = render(<SkeletonText width="3/4" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-3/4')
    })

    it('renders with configurable width - 1/2 @unit', () => {
      const { container } = render(<SkeletonText width="1/2" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-1/2')
    })

    it('renders with configurable width - 1/3 @unit', () => {
      const { container } = render(<SkeletonText width="1/3" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-1/3')
    })

    it('renders with configurable width - 1/4 @unit', () => {
      const { container } = render(<SkeletonText width="1/4" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-1/4')
    })

    it('renders with configurable width - 2/3 @unit', () => {
      const { container } = render(<SkeletonText width="2/3" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-2/3')
    })

    it('has default height of h-4 @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-4')
    })

    it('has aria-hidden="true" for accessibility @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('aria-hidden', 'true')
    })

    it('has role="presentation" for accessibility @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('role', 'presentation')
    })

    it('applies animation classes @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('merges custom className properly @unit', () => {
      const { container } = render(<SkeletonText className="custom-text h-6" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('custom-text')
      expect(skeleton).toHaveClass('h-6')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('applies rounded variant - md (default) @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-md')
    })

    it('applies rounded variant - full @unit', () => {
      const { container } = render(<SkeletonText rounded="full" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-full')
    })

    it('accepts and applies data-testid @unit', () => {
      render(<SkeletonText data-testid="custom-text-skeleton" />)
      expect(screen.getByTestId('custom-text-skeleton')).toBeInTheDocument()
    })
  })

  describe('SkeletonCircle', () => {
    it('renders without crashing @unit', () => {
      const { container } = render(<SkeletonCircle />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders with size variant - xs @unit', () => {
      const { container } = render(<SkeletonCircle size="xs" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-6')
      expect(skeleton).toHaveClass('w-6')
    })

    it('renders with size variant - sm @unit', () => {
      const { container } = render(<SkeletonCircle size="sm" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-8')
      expect(skeleton).toHaveClass('w-8')
    })

    it('renders with size variant - md (default) @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-10')
      expect(skeleton).toHaveClass('w-10')
    })

    it('renders with size variant - lg @unit', () => {
      const { container } = render(<SkeletonCircle size="lg" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-12')
      expect(skeleton).toHaveClass('w-12')
    })

    it('renders with size variant - xl @unit', () => {
      const { container } = render(<SkeletonCircle size="xl" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-16')
      expect(skeleton).toHaveClass('w-16')
    })

    it('applies rounded-full class @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-full')
    })

    it('has aria-hidden="true" for accessibility @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('aria-hidden', 'true')
    })

    it('has role="presentation" for accessibility @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('role', 'presentation')
    })

    it('applies animation classes @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('merges custom className properly @unit', () => {
      const { container } = render(<SkeletonCircle className="custom-circle" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('custom-circle')
      expect(skeleton).toHaveClass('bg-muted')
      expect(skeleton).toHaveClass('rounded-full')
    })

    it('allows custom size via className @unit', () => {
      const { container } = render(<SkeletonCircle className="h-24 w-24" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-24')
      expect(skeleton).toHaveClass('w-24')
    })

    it('accepts and applies data-testid @unit', () => {
      render(<SkeletonCircle data-testid="custom-circle-skeleton" />)
      expect(screen.getByTestId('custom-circle-skeleton')).toBeInTheDocument()
    })
  })

  describe('SkeletonBlock', () => {
    it('renders without crashing @unit', () => {
      const { container } = render(<SkeletonBlock />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders with height variant - xs @unit', () => {
      const { container } = render(<SkeletonBlock height="xs" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-16')
    })

    it('renders with height variant - sm @unit', () => {
      const { container } = render(<SkeletonBlock height="sm" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-24')
    })

    it('renders with height variant - md (default) @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-32')
    })

    it('renders with height variant - lg @unit', () => {
      const { container } = render(<SkeletonBlock height="lg" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-48')
    })

    it('renders with height variant - xl @unit', () => {
      const { container } = render(<SkeletonBlock height="xl" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-64')
    })

    it('applies default full width @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('w-full')
    })

    it('applies rounded variant - none @unit', () => {
      const { container } = render(<SkeletonBlock rounded="none" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-none')
    })

    it('applies rounded variant - md (default) @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-md')
    })

    it('applies rounded variant - lg @unit', () => {
      const { container } = render(<SkeletonBlock rounded="lg" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-lg')
    })

    it('applies rounded variant - xl @unit', () => {
      const { container } = render(<SkeletonBlock rounded="xl" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('rounded-xl')
    })

    it('has aria-hidden="true" for accessibility @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('aria-hidden', 'true')
    })

    it('has role="presentation" for accessibility @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveAttribute('role', 'presentation')
    })

    it('applies animation classes @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
      expect(skeleton).toHaveClass('bg-muted')
    })

    it('merges custom className properly @unit', () => {
      const { container } = render(<SkeletonBlock className="custom-block" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('custom-block')
      expect(skeleton).toHaveClass('bg-muted')
      expect(skeleton).toHaveClass('w-full')
    })

    it('allows custom dimensions via className @unit', () => {
      const { container } = render(<SkeletonBlock className="h-96 w-1/2" />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('h-96')
      expect(skeleton).toHaveClass('w-1/2')
    })

    it('accepts and applies data-testid @unit', () => {
      render(<SkeletonBlock data-testid="custom-block-skeleton" />)
      expect(screen.getByTestId('custom-block-skeleton')).toBeInTheDocument()
    })
  })

  describe('Animation and Reduced Motion', () => {
    it('Skeleton applies animate-pulse by default @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('SkeletonText applies animate-pulse by default @unit', () => {
      const { container } = render(<SkeletonText />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('SkeletonCircle applies animate-pulse by default @unit', () => {
      const { container } = render(<SkeletonCircle />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('SkeletonBlock applies animate-pulse by default @unit', () => {
      const { container } = render(<SkeletonBlock />)
      const skeleton = container.firstChild as HTMLElement

      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('applies shimmer animation classes for enhanced loading effect @unit', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.firstChild as HTMLElement

      // Check for shimmer gradient classes
      expect(skeleton.className).toContain('before:animate-shimmer')
      expect(skeleton.className).toContain('before:bg-gradient-to-r')
    })
  })

  describe('Common Use Cases', () => {
    it('renders a loading card skeleton @unit', () => {
      const { container } = render(
        <div className="space-y-4">
          <SkeletonCircle size="lg" />
          <SkeletonText width="3/4" />
          <SkeletonText width="1/2" />
          <SkeletonBlock height="sm" />
        </div>
      )

      const skeletons = container.querySelectorAll('[aria-hidden="true"]')
      expect(skeletons).toHaveLength(4)
    })

    it('renders a user profile skeleton @unit', () => {
      render(
        <div className="flex gap-4" data-testid="profile-skeleton">
          <SkeletonCircle size="xl" />
          <div className="flex-1 space-y-2">
            <SkeletonText width="1/2" />
            <SkeletonText width="3/4" />
          </div>
        </div>
      )

      expect(screen.getByTestId('profile-skeleton')).toBeInTheDocument()
    })

    it('renders a list of skeleton items @unit', () => {
      const { container } = render(
        <div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2 mb-4">
              <SkeletonText width="full" />
              <SkeletonText width="3/4" />
            </div>
          ))}
        </div>
      )

      const skeletons = container.querySelectorAll('[aria-hidden="true"]')
      // 3 items * 2 text skeletons = 6 total
      expect(skeletons).toHaveLength(6)
    })
  })

  describe('Accessibility Compliance', () => {
    it('all skeleton components are hidden from screen readers @unit', () => {
      const { container } = render(
        <div>
          <Skeleton className="h-4 w-full" />
          <SkeletonText />
          <SkeletonCircle />
          <SkeletonBlock />
        </div>
      )

      const skeletons = container.querySelectorAll('[aria-hidden="true"]')
      expect(skeletons).toHaveLength(4)
    })

    it('all skeleton components have presentation role @unit', () => {
      const { container } = render(
        <div>
          <Skeleton className="h-4 w-full" />
          <SkeletonText />
          <SkeletonCircle />
          <SkeletonBlock />
        </div>
      )

      const skeletons = container.querySelectorAll('[role="presentation"]')
      expect(skeletons).toHaveLength(4)
    })

    it('skeleton components do not interfere with keyboard navigation @unit', () => {
      const { container } = render(
        <div>
          <button type="button">Before</button>
          <SkeletonBlock />
          <button type="button">After</button>
        </div>
      )

      const buttons = container.querySelectorAll('button')
      expect(buttons).toHaveLength(2)

      // Skeleton should not have tabIndex
      const skeleton = container.querySelector('[aria-hidden="true"]')
      expect(skeleton).not.toHaveAttribute('tabindex')
    })
  })
})
