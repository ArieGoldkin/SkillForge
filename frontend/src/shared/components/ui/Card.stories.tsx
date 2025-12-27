import type { Meta, StoryObj } from '@storybook/react-vite'
import { AlertCircle, Bell, Calendar } from 'lucide-react'

import { Button } from './button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './card'

/**
 * Card components for displaying content in a contained, elevated surface
 * Follows shadcn/ui patterns with SkillForge theme
 */
const meta = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Card>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Basic card with title and description
 */
export const Default: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
        <CardDescription>Card description goes here</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm">This is the main content area of the card.</p>
      </CardContent>
    </Card>
  ),
}

/**
 * Card with header, content, and footer
 */
export const WithFooter: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
        <CardDescription>You have 3 unread messages</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <Bell className="h-4 w-4 text-primary" />
            <span>New analysis completed</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-primary" />
            <span>Meeting scheduled for tomorrow</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle className="h-4 w-4 text-destructive" />
            <span>Action required: Review pending</span>
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="outline" className="w-full">
          View All
        </Button>
      </CardFooter>
    </Card>
  ),
}

/**
 * Card with action buttons in footer
 */
export const WithActions: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardHeader>
        <CardTitle>Analysis Complete</CardTitle>
        <CardDescription>Your document analysis is ready</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          The analysis has identified 12 key insights and 5 action items. Review the full report to
          learn more.
        </p>
      </CardContent>
      <CardFooter className="gap-2">
        <Button variant="outline" className="flex-1">
          Cancel
        </Button>
        <Button variant="default" className="flex-1">
          View Report
        </Button>
      </CardFooter>
    </Card>
  ),
}

/**
 * Minimal card with just content
 */
export const ContentOnly: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardContent className="pt-6">
        <p className="text-sm">
          This card only has content, no header or footer. Useful for simple layouts.
        </p>
      </CardContent>
    </Card>
  ),
}

/**
 * Card with icon in header
 */
export const WithIcon: Story = {
  render: () => (
    <Card className="w-[380px]">
      <CardHeader>
        <div className="flex items-start gap-4">
          <div className="rounded-full bg-primary/10 p-2">
            <Calendar className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <CardTitle>Upcoming Event</CardTitle>
            <CardDescription>Tomorrow at 2:00 PM</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm">Team sync meeting to discuss project progress and next steps.</p>
      </CardContent>
    </Card>
  ),
}

/**
 * Interactive card with hover effect
 */
export const Interactive: Story = {
  render: () => (
    <Card className="w-[380px] cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02]">
      <CardHeader>
        <CardTitle>Click me</CardTitle>
        <CardDescription>This card has hover effects</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Hover over this card to see the elevation and scale effects.
        </p>
      </CardContent>
    </Card>
  ),
}

/**
 * Grid of cards
 */
export const CardGrid: Story = {
  render: () => (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader>
            <CardTitle>Analysis {i}</CardTitle>
            <CardDescription>Created 2 hours ago</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Summary of analysis findings and key insights discovered.
            </p>
          </CardContent>
          <CardFooter>
            <Button variant="ghost" size="sm" className="w-full">
              View Details
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  ),
}

/**
 * Card with custom styling
 */
export const CustomStyling: Story = {
  render: () => (
    <Card className="w-[380px] border-primary/50 bg-primary/5">
      <CardHeader>
        <CardTitle className="text-primary">Featured Analysis</CardTitle>
        <CardDescription>Highlighted for your attention</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm">This card uses custom styling to stand out from others.</p>
      </CardContent>
    </Card>
  ),
}
