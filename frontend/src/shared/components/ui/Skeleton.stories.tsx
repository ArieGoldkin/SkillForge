/* eslint-disable max-lines */
import type { Meta, StoryObj } from '@storybook/react-vite'

import { Card, CardContent, CardHeader } from './card'
import { Skeleton, SkeletonBlock, SkeletonCircle, SkeletonText } from './skeleton'

/**
 * Skeleton components for loading states with shimmer animation
 * WCAG 2.1 AA compliant with proper ARIA attributes
 */
const meta = {
  title: 'UI/Skeleton',
  component: Skeleton,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Skeleton>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Basic skeleton with custom dimensions
 */
export const Default: Story = {
  render: () => <Skeleton className="h-12 w-[250px]" />,
}

/**
 * Skeleton with different border radius options
 */
export const BorderRadius: Story = {
  render: () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">None</p>
        <Skeleton rounded="none" className="h-12 w-[250px]" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Small</p>
        <Skeleton rounded="sm" className="h-12 w-[250px]" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Medium</p>
        <Skeleton rounded="md" className="h-12 w-[250px]" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Large</p>
        <Skeleton rounded="lg" className="h-12 w-[250px]" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Full</p>
        <Skeleton rounded="full" className="h-12 w-[250px]" />
      </div>
    </div>
  ),
}

/**
 * Skeleton text with different widths
 */
export const TextVariants: Story = {
  render: () => (
    <div className="space-y-2 w-[400px]">
      <SkeletonText width="full" />
      <SkeletonText width="3/4" />
      <SkeletonText width="2/3" />
      <SkeletonText width="1/2" />
      <SkeletonText width="1/3" />
      <SkeletonText width="1/4" />
    </div>
  ),
}

/**
 * Skeleton circles for avatars/icons
 */
export const CircleVariants: Story = {
  render: () => (
    <div className="flex items-end gap-4">
      <SkeletonCircle size="xs" />
      <SkeletonCircle size="sm" />
      <SkeletonCircle size="md" />
      <SkeletonCircle size="lg" />
      <SkeletonCircle size="xl" />
    </div>
  ),
}

/**
 * Skeleton blocks for content areas
 */
export const BlockVariants: Story = {
  render: () => (
    <div className="space-y-4 w-[400px]">
      <SkeletonBlock height="xs" />
      <SkeletonBlock height="sm" />
      <SkeletonBlock height="md" />
      <SkeletonBlock height="lg" />
      <SkeletonBlock height="xl" />
    </div>
  ),
}

/**
 * Profile card loading state
 */
export const ProfileCard: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <div className="flex items-center gap-4">
          <SkeletonCircle size="lg" />
          <div className="flex-1 space-y-2">
            <SkeletonText width="3/4" className="h-5" />
            <SkeletonText width="1/2" className="h-4" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <SkeletonText width="full" />
          <SkeletonText width="full" />
          <SkeletonText width="2/3" />
        </div>
      </CardContent>
    </Card>
  ),
}

/**
 * Article card loading state
 */
export const ArticleCard: Story = {
  render: () => (
    <Card className="w-[400px]">
      <SkeletonBlock height="lg" rounded="none" />
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <SkeletonText width="3/4" className="h-6" />
          <SkeletonText width="1/2" className="h-4" />
        </div>
        <div className="space-y-2">
          <SkeletonText width="full" />
          <SkeletonText width="full" />
          <SkeletonText width="2/3" />
        </div>
        <div className="flex items-center gap-2">
          <SkeletonCircle size="sm" />
          <SkeletonText width="1/4" />
        </div>
      </CardContent>
    </Card>
  ),
}

/**
 * List items loading state
 */
export const ListItems: Story = {
  render: () => (
    <div className="w-[400px] space-y-3">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-3 p-3 border rounded-lg">
          <SkeletonCircle size="md" />
          <div className="flex-1 space-y-2">
            <SkeletonText width="3/4" />
            <SkeletonText width="1/2" className="h-3" />
          </div>
        </div>
      ))}
    </div>
  ),
}

/**
 * Table loading state
 */
export const Table: Story = {
  render: () => (
    <div className="w-[600px] space-y-2">
      <div className="grid grid-cols-4 gap-4 p-3 bg-muted/50 rounded-t-lg">
        <SkeletonText width="3/4" className="h-4" />
        <SkeletonText width="2/3" className="h-4" />
        <SkeletonText width="1/2" className="h-4" />
        <SkeletonText width="3/4" className="h-4" />
      </div>
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="grid grid-cols-4 gap-4 p-3 border-b">
          <SkeletonText width="full" />
          <SkeletonText width="full" />
          <SkeletonText width="full" />
          <SkeletonText width="full" />
        </div>
      ))}
    </div>
  ),
}

/**
 * Dashboard grid loading state
 */
export const DashboardGrid: Story = {
  render: () => (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <Card key={i}>
          <CardHeader>
            <SkeletonText width="2/3" className="h-5" />
            <SkeletonText width="1/2" className="h-4" />
          </CardHeader>
          <CardContent>
            <SkeletonBlock height="sm" />
          </CardContent>
        </Card>
      ))}
    </div>
  ),
}

/**
 * Form loading state
 */
export const Form: Story = {
  render: () => (
    <div className="w-[400px] space-y-6">
      <div className="space-y-2">
        <SkeletonText width="1/4" className="h-4" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="space-y-2">
        <SkeletonText width="1/3" className="h-4" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="space-y-2">
        <SkeletonText width="1/4" className="h-4" />
        <Skeleton className="h-24 w-full" />
      </div>
      <Skeleton className="h-10 w-32" />
    </div>
  ),
}
