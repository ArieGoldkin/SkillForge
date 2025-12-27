/* eslint-disable max-lines */
import { useEffect, useState } from 'react'

import type { Meta, StoryObj } from '@storybook/react-vite'

import { Progress } from './progress'

/**
 * Accessible progress bar component with multiple variants
 * WCAG 2.1 AA compliant with proper ARIA attributes
 */
const meta = {
  title: 'UI/Progress',
  component: Progress,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    value: {
      control: { type: 'range', min: 0, max: 100, step: 1 },
      description: 'Progress value (0-100)',
    },
    variant: {
      control: 'select',
      options: ['default', 'success', 'warning', 'error', 'muted'],
      description: 'Visual variant',
    },
  },
} satisfies Meta<typeof Progress>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Default progress bar with teal accent
 */
export const Default: Story = {
  args: {
    value: 50,
    variant: 'default',
    'aria-label': 'Upload progress',
  },
  render: (args) => (
    <div className="w-[400px]">
      <Progress {...args} />
    </div>
  ),
}

/**
 * Success variant (green)
 */
export const Success: Story = {
  args: {
    value: 100,
    variant: 'success',
    'aria-label': 'Completion progress',
  },
  render: (args) => (
    <div className="w-[400px]">
      <Progress {...args} />
    </div>
  ),
}

/**
 * Warning variant (yellow)
 */
export const Warning: Story = {
  args: {
    value: 75,
    variant: 'warning',
    'aria-label': 'Storage usage',
  },
  render: (args) => (
    <div className="w-[400px]">
      <Progress {...args} />
    </div>
  ),
}

/**
 * Error variant (red)
 */
export const ErrorVariant: Story = {
  args: {
    value: 30,
    variant: 'error',
    'aria-label': 'Error rate',
  },
  render: (args) => (
    <div className="w-[400px]">
      <Progress {...args} />
    </div>
  ),
}

/**
 * Muted variant (gray)
 */
export const Muted: Story = {
  args: {
    value: 60,
    variant: 'muted',
    'aria-label': 'Background task progress',
  },
  render: (args) => (
    <div className="w-[400px]">
      <Progress {...args} />
    </div>
  ),
}

/**
 * Different progress values
 */
export const Values: Story = {
  render: () => (
    <div className="w-[400px] space-y-6">
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>0%</span>
          <span className="text-muted-foreground">Just started</span>
        </div>
        <Progress value={0} />
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>25%</span>
          <span className="text-muted-foreground">Quarter way</span>
        </div>
        <Progress value={25} />
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>50%</span>
          <span className="text-muted-foreground">Halfway</span>
        </div>
        <Progress value={50} />
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>75%</span>
          <span className="text-muted-foreground">Almost there</span>
        </div>
        <Progress value={75} />
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>100%</span>
          <span className="text-muted-foreground">Complete</span>
        </div>
        <Progress value={100} variant="success" />
      </div>
    </div>
  ),
}

/**
 * All variants showcase
 */
export const AllVariants: Story = {
  render: () => (
    <div className="w-[400px] space-y-6">
      <div className="space-y-2">
        <p className="text-sm font-medium">Default (Teal)</p>
        <Progress value={65} variant="default" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Success (Green)</p>
        <Progress value={100} variant="success" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Warning (Yellow)</p>
        <Progress value={75} variant="warning" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Error (Red)</p>
        <Progress value={30} variant="error" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Muted (Gray)</p>
        <Progress value={50} variant="muted" />
      </div>
    </div>
  ),
}

/**
 * Animated progress (simulates upload)
 */
export const Animated: Story = {
  render: () => {
    const [progress, setProgress] = useState(0)

    useEffect(() => {
      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            return 0
          }
          return prev + 1
        })
      }, 50)

      return () => clearInterval(timer)
    }, [])

    return (
      <div className="w-[400px] space-y-2">
        <div className="flex justify-between text-sm">
          <span>Uploading file...</span>
          <span className="font-medium">{progress}%</span>
        </div>
        <Progress value={progress} variant={progress === 100 ? 'success' : 'default'} />
      </div>
    )
  },
}

/**
 * Multi-step progress
 */
export const MultiStep: Story = {
  render: () => {
    const steps = [
      { label: 'Analyzing document', progress: 100, variant: 'success' as const },
      { label: 'Extracting insights', progress: 100, variant: 'success' as const },
      { label: 'Generating summary', progress: 60, variant: 'default' as const },
      { label: 'Creating report', progress: 0, variant: 'muted' as const },
    ]

    return (
      <div className="w-[500px] space-y-4">
        {steps.map((step, index) => (
          // eslint-disable-next-line react/no-array-index-key
          <div key={index} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className={step.progress === 100 ? 'text-muted-foreground' : ''}>
                {index + 1}. {step.label}
              </span>
              <span className="font-medium">{step.progress}%</span>
            </div>
            <Progress value={step.progress} variant={step.variant} />
          </div>
        ))}
      </div>
    )
  },
}

/**
 * With custom aria-valuetext
 */
export const CustomAriaValueText: Story = {
  render: () => (
    <div className="w-[400px] space-y-2">
      <p className="text-sm">Analysis Progress</p>
      <Progress
        value={75}
        aria-label="Document analysis progress"
        aria-valuetext="3 out of 4 sections analyzed"
      />
      <p className="text-xs text-muted-foreground">3 out of 4 sections analyzed</p>
    </div>
  ),
}

/**
 * Indeterminate loading (using animated variant)
 */
export const IndeterminateLoading: Story = {
  render: () => {
    const [position, setPosition] = useState(0)

    useEffect(() => {
      const timer = setInterval(() => {
        setPosition((prev) => (prev + 2) % 200)
      }, 20)

      return () => clearInterval(timer)
    }, [])

    const value = position > 100 ? 200 - position : position

    return (
      <div className="w-[400px] space-y-2">
        <p className="text-sm">Processing...</p>
        <Progress value={value} variant="default" />
        <p className="text-xs text-muted-foreground">Please wait while we process your request</p>
      </div>
    )
  },
}
