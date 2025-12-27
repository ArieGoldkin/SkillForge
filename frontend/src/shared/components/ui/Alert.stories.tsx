/* eslint-disable max-lines */
import type { Meta, StoryObj } from '@storybook/react-vite'
import { AlertCircle, CheckCircle2, Info, Terminal, XCircle } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from './alert'

/**
 * Alert component for displaying important messages
 * Follows shadcn/ui patterns with SkillForge theme
 */
const meta = {
  title: 'UI/Alert',
  component: Alert,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'destructive'],
      description: 'Visual variant',
    },
  },
} satisfies Meta<typeof Alert>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Default alert with info icon
 */
export const Default: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <Info className="h-4 w-4" />
      <AlertTitle>Information</AlertTitle>
      <AlertDescription>This is a default alert with important information.</AlertDescription>
    </Alert>
  ),
}

/**
 * Destructive alert for errors
 */
export const Destructive: Story = {
  render: () => (
    <Alert variant="destructive" className="w-[500px]">
      <XCircle className="h-4 w-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>
        Something went wrong. Please try again or contact support.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * Success alert (custom styling)
 */
export const Success: Story = {
  render: () => (
    <Alert className="w-[500px] border-green-500/50 bg-green-50 dark:bg-green-950/20">
      <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
      <AlertTitle className="text-green-900 dark:text-green-100">Success</AlertTitle>
      <AlertDescription className="text-green-800 dark:text-green-200">
        Your analysis has been completed successfully.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * Warning alert (custom styling)
 */
export const Warning: Story = {
  render: () => (
    <Alert className="w-[500px] border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
      <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
      <AlertTitle className="text-yellow-900 dark:text-yellow-100">Warning</AlertTitle>
      <AlertDescription className="text-yellow-800 dark:text-yellow-200">
        Your storage is almost full. Consider deleting old analyses.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * Alert with only description
 */
export const DescriptionOnly: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <Info className="h-4 w-4" />
      <AlertDescription>
        This alert only has a description without a title. Useful for shorter messages.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * Alert with only title
 */
export const TitleOnly: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <Terminal className="h-4 w-4" />
      <AlertTitle>System Update Available</AlertTitle>
    </Alert>
  ),
}

/**
 * Alert without icon
 */
export const NoIcon: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <AlertTitle>No Icon</AlertTitle>
      <AlertDescription>This alert has no icon, just text content.</AlertDescription>
    </Alert>
  ),
}

/**
 * Alert with rich content
 */
export const RichContent: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <Info className="h-4 w-4" />
      <AlertTitle>Analysis Complete</AlertTitle>
      <AlertDescription>
        <p className="mb-2">Your document has been analyzed. Key findings:</p>
        <ul className="list-disc list-inside space-y-1 text-sm">
          <li>12 sections identified</li>
          <li>5 action items extracted</li>
          <li>3 potential issues detected</li>
        </ul>
      </AlertDescription>
    </Alert>
  ),
}

/**
 * All variants showcase
 */
export const AllVariants: Story = {
  render: () => (
    <div className="space-y-4 w-[500px]">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Information</AlertTitle>
        <AlertDescription>Default alert for general information.</AlertDescription>
      </Alert>

      <Alert className="border-green-500/50 bg-green-50 dark:bg-green-950/20">
        <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
        <AlertTitle className="text-green-900 dark:text-green-100">Success</AlertTitle>
        <AlertDescription className="text-green-800 dark:text-green-200">
          Operation completed successfully.
        </AlertDescription>
      </Alert>

      <Alert className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
        <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
        <AlertTitle className="text-yellow-900 dark:text-yellow-100">Warning</AlertTitle>
        <AlertDescription className="text-yellow-800 dark:text-yellow-200">
          Please review this before continuing.
        </AlertDescription>
      </Alert>

      <Alert variant="destructive">
        <XCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>An error occurred during processing.</AlertDescription>
      </Alert>
    </div>
  ),
}

/**
 * Stacked alerts
 */
export const Stacked: Story = {
  render: () => (
    <div className="space-y-3 w-[500px]">
      <Alert>
        <Terminal className="h-4 w-4" />
        <AlertTitle>System Maintenance</AlertTitle>
        <AlertDescription>Scheduled maintenance on Dec 28, 2025 at 2:00 AM UTC.</AlertDescription>
      </Alert>

      <Alert className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
        <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
        <AlertTitle className="text-yellow-900 dark:text-yellow-100">Storage Warning</AlertTitle>
        <AlertDescription className="text-yellow-800 dark:text-yellow-200">
          You've used 85% of your storage quota.
        </AlertDescription>
      </Alert>

      <Alert className="border-green-500/50 bg-green-50 dark:bg-green-950/20">
        <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
        <AlertTitle className="text-green-900 dark:text-green-100">Backup Complete</AlertTitle>
        <AlertDescription className="text-green-800 dark:text-green-200">
          Your data has been backed up successfully.
        </AlertDescription>
      </Alert>
    </div>
  ),
}

/**
 * Compact alert
 */
export const Compact: Story = {
  render: () => (
    <Alert className="w-[500px] py-2">
      <Info className="h-4 w-4" />
      <AlertDescription className="text-xs">
        Compact alert with smaller padding and text size.
      </AlertDescription>
    </Alert>
  ),
}

/**
 * Alert with action button
 */
export const WithAction: Story = {
  render: () => (
    <Alert className="w-[500px]">
      <Info className="h-4 w-4" />
      <div className="flex-1">
        <AlertTitle>New Version Available</AlertTitle>
        <AlertDescription>
          Version 2.0 is now available with new features and improvements.
        </AlertDescription>
      </div>
      <button
        type="button"
        className="mt-2 px-3 py-1 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
      >
        Update Now
      </button>
    </Alert>
  ),
}
