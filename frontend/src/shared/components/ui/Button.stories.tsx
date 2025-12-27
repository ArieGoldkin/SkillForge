import type { Meta, StoryObj } from '@storybook/react-vite'
import { CheckCircle, Loader2, Upload } from 'lucide-react'

import { Button } from './button'

/**
 * Button component based on shadcn/ui with SkillForge theme
 * Supports multiple variants, sizes, and custom icons
 */
const meta = {
  title: 'UI/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link', 'teal'],
      description: 'Visual style variant',
    },
    size: {
      control: 'select',
      options: ['default', 'sm', 'lg', 'icon'],
      description: 'Button size',
    },
    disabled: {
      control: 'boolean',
      description: 'Disabled state',
    },
    asChild: {
      control: 'boolean',
      description: 'Render as Slot component',
    },
  },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Default primary button with teal accent
 */
export const Default: Story = {
  args: {
    children: 'Button',
    variant: 'default',
    size: 'default',
  },
}

/**
 * Destructive button for dangerous actions (delete, remove)
 */
export const Destructive: Story = {
  args: {
    children: 'Delete',
    variant: 'destructive',
  },
}

/**
 * Outline button for secondary actions
 */
export const Outline: Story = {
  args: {
    children: 'Outline',
    variant: 'outline',
  },
}

/**
 * Secondary button with subtle background
 */
export const Secondary: Story = {
  args: {
    children: 'Secondary',
    variant: 'secondary',
  },
}

/**
 * Ghost button with no background
 */
export const Ghost: Story = {
  args: {
    children: 'Ghost',
    variant: 'ghost',
  },
}

/**
 * Link-styled button
 */
export const Link: Story = {
  args: {
    children: 'Link',
    variant: 'link',
  },
}

/**
 * Teal accent button with enhanced shadow
 */
export const Teal: Story = {
  args: {
    children: 'Teal',
    variant: 'teal',
  },
}

/**
 * Small button
 */
export const Small: Story = {
  args: {
    children: 'Small',
    size: 'sm',
  },
}

/**
 * Large button
 */
export const Large: Story = {
  args: {
    children: 'Large',
    size: 'lg',
  },
}

/**
 * Icon-only button
 */
export const Icon: Story = {
  args: {
    size: 'icon',
    children: <Upload className="h-4 w-4" />,
  },
}

/**
 * Button with left icon
 */
export const WithIconLeft: Story = {
  args: {
    children: (
      <>
        <CheckCircle className="h-4 w-4" />
        Success
      </>
    ),
  },
}

/**
 * Button with right icon
 */
export const WithIconRight: Story = {
  args: {
    children: (
      <>
        Upload
        <Upload className="h-4 w-4" />
      </>
    ),
  },
}

/**
 * Loading state with spinner
 */
export const Loading: Story = {
  args: {
    disabled: true,
    children: (
      <>
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </>
    ),
  },
}

/**
 * Disabled button
 */
export const Disabled: Story = {
  args: {
    children: 'Disabled',
    disabled: true,
  },
}

/**
 * All variants showcase
 */
export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <Button variant="default">Default</Button>
      <Button variant="destructive">Destructive</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="link">Link</Button>
      <Button variant="teal">Teal</Button>
    </div>
  ),
}

/**
 * All sizes showcase
 */
export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Button size="sm">Small</Button>
      <Button size="default">Default</Button>
      <Button size="lg">Large</Button>
      <Button size="icon">
        <Upload className="h-4 w-4" />
      </Button>
    </div>
  ),
}
