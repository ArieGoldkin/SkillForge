import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { MarkdownPreview } from '../index'

describe('CollapsibleSection Component', () => {
  it('should render details element with React state management', () => {
    const markdown = `
<details>
<summary>Test Summary</summary>
Test content inside details
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const details = container.querySelector('details')
    const summary = container.querySelector('summary')

    expect(details).toBeInTheDocument()
    expect(summary).toBeInTheDocument()
    expect(summary).toHaveTextContent('Test Summary')
  })

  it('should start in closed state by default', () => {
    const markdown = `
<details>
<summary>Click me</summary>
Hidden content
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const details = container.querySelector('details')
    expect(details).not.toHaveAttribute('open')
  })

  it('should respect initial open attribute', () => {
    const markdown = `
<details open>
<summary>Initially Open</summary>
Visible content
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const details = container.querySelector('details')
    expect(details).toHaveAttribute('open')
  })

  it('should toggle open state on summary click', async () => {
    const user = userEvent.setup()
    const markdown = `
<details>
<summary>Toggle This</summary>
Content to show/hide
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const summary = screen.getByText('Toggle This')
    const details = container.querySelector('details')

    // Should start closed
    expect(details).not.toHaveAttribute('open')

    // Click to open
    await user.click(summary)
    expect(details).toHaveAttribute('open')

    // Click to close
    await user.click(summary)
    expect(details).not.toHaveAttribute('open')

    // Click to open again
    await user.click(summary)
    expect(details).toHaveAttribute('open')
  })

  it('should handle nested markdown content inside details', () => {
    const markdown = `
<details>
<summary>Solution</summary>

## Nested Heading

This is a **bold** paragraph with *italic* text.

- List item 1
- List item 2

\`\`\`python
def solution():
    return 42
\`\`\`

</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    // Check for nested markdown elements
    expect(screen.getByText('Nested Heading')).toBeInTheDocument()
    expect(container.querySelector('h2')).toBeInTheDocument()
    expect(container.querySelector('strong')).toHaveTextContent('bold')
    expect(container.querySelector('em')).toHaveTextContent('italic')
    expect(container.querySelector('ul')).toBeInTheDocument()

    // Check for code block
    const codeBlock = container.querySelector('code[data-testid="code-block"]')
    expect(codeBlock).toBeInTheDocument()
  })

  it('should handle multiple independent collapsible sections', async () => {
    const user = userEvent.setup()
    const markdown = `
<details>
<summary>Section 1</summary>
Content 1
</details>

<details>
<summary>Section 2</summary>
Content 2
</details>

<details>
<summary>Section 3</summary>
Content 3
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const details = container.querySelectorAll('details')
    expect(details).toHaveLength(3)

    // All should start closed
    details.forEach((detail) => {
      expect(detail).not.toHaveAttribute('open')
    })

    // Open first section
    await user.click(screen.getByText('Section 1'))
    expect(details[0]).toHaveAttribute('open')
    expect(details[1]).not.toHaveAttribute('open')
    expect(details[2]).not.toHaveAttribute('open')

    // Open second section (first should stay open)
    await user.click(screen.getByText('Section 2'))
    expect(details[0]).toHaveAttribute('open')
    expect(details[1]).toHaveAttribute('open')
    expect(details[2]).not.toHaveAttribute('open')

    // Close first section
    await user.click(screen.getByText('Section 1'))
    expect(details[0]).not.toHaveAttribute('open')
    expect(details[1]).toHaveAttribute('open')
    expect(details[2]).not.toHaveAttribute('open')
  })

  it('should handle complex nested structures', () => {
    const markdown = `
<details>
<summary>Main Question</summary>

### Problem Statement

Here's the problem description.

<details>
<summary>Hint 1</summary>
First hint content
</details>

<details>
<summary>Hint 2</summary>
Second hint content
</details>

### Solution

<details>
<summary>Final Answer</summary>

\`\`\`javascript
console.log("answer");
\`\`\`

</details>

</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const allDetails = container.querySelectorAll('details')
    expect(allDetails).toHaveLength(4) // 1 main + 3 nested

    expect(screen.getByText('Main Question')).toBeInTheDocument()
    expect(screen.getByText('Hint 1')).toBeInTheDocument()
    expect(screen.getByText('Hint 2')).toBeInTheDocument()
    expect(screen.getByText('Final Answer')).toBeInTheDocument()
  })

  it('should apply CSS classes for styling', () => {
    const markdown = `
<details class="custom-class">
<summary class="custom-summary">Styled Section</summary>
Content here
</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const details = container.querySelector('details')
    const summary = container.querySelector('summary')

    expect(details).toHaveClass('custom-class')
    expect(summary).toHaveClass('custom-summary')
  })

  it('should work with task lists inside details', async () => {
    const user = userEvent.setup()
    const markdown = `
<details>
<summary>Todo List</summary>

- [x] Completed task
- [ ] Pending task
- [ ] Another task

</details>
`
    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const summary = screen.getByText('Todo List')

    // Initially closed, but content is in DOM
    expect(screen.getByText('Completed task')).toBeInTheDocument()

    // Open details
    await user.click(summary)

    // Check for checkboxes
    const checkboxes = container.querySelectorAll('input[type="checkbox"]')
    expect(checkboxes).toHaveLength(3)
    expect(checkboxes[0]).toBeChecked()
    expect(checkboxes[1]).not.toBeChecked()
    expect(checkboxes[2]).not.toBeChecked()
  })
})
