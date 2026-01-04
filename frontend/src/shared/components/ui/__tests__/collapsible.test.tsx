import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../collapsible'

describe('Collapsible', () => {
  it('renders trigger and hides content by default', () => {
    render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    expect(screen.getByText('Toggle')).toBeInTheDocument()
    // Content should be hidden when defaultOpen is not set (defaults to false)
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('hides content by default', () => {
    render(
      <Collapsible defaultOpen={false}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('shows content when defaultOpen is true', () => {
    render(
      <Collapsible defaultOpen={true}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('toggles content visibility when trigger is clicked', async () => {
    const user = userEvent.setup()
    render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    const trigger = screen.getByText('Toggle')
    expect(screen.queryByText('Content')).not.toBeInTheDocument()

    await user.click(trigger)
    expect(screen.getByText('Content')).toBeInTheDocument()

    await user.click(trigger)
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('supports controlled mode with open prop', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <Collapsible open={false} onOpenChange={onOpenChange}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    expect(screen.queryByText('Content')).not.toBeInTheDocument()

    const trigger = screen.getByText('Toggle')
    await user.click(trigger)

    expect(onOpenChange).toHaveBeenCalledWith(true)
    // Content should still be hidden (controlled)
    expect(screen.queryByText('Content')).not.toBeInTheDocument()

    // Update open prop
    rerender(
      <Collapsible open={true} onOpenChange={onOpenChange}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('sets correct ARIA attributes', () => {
    render(
      <Collapsible defaultOpen={false}>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    const trigger = screen.getByRole('button')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
  })

  it('updates ARIA attributes when opened', async () => {
    const user = userEvent.setup()
    render(
      <Collapsible>
        <CollapsibleTrigger>Toggle</CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    const trigger = screen.getByRole('button')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })

  it('supports asChild prop for custom trigger', async () => {
    const user = userEvent.setup()
    render(
      <Collapsible>
        <CollapsibleTrigger asChild>
          <button type="button">Custom Trigger</button>
        </CollapsibleTrigger>
        <CollapsibleContent>Content</CollapsibleContent>
      </Collapsible>
    )

    const trigger = screen.getByText('Custom Trigger')
    await user.click(trigger)

    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })
})
