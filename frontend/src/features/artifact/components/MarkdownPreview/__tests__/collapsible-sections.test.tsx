import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { MarkdownPreview } from '../index'

describe('MarkdownPreview - Collapsible Sections', () => {
  it('renders details/summary HTML tags from markdown', () => {
    const markdown = `
# Test Document

<details>
<summary>Click to expand</summary>

This content is hidden by default.

\`\`\`python
print("Hello, World!")
\`\`\`

</details>
`

    render(<MarkdownPreview content={markdown} showMetadata={false} />)

    // Summary should be visible
    expect(screen.getByText('Click to expand')).toBeInTheDocument()

    // Content should be in the DOM (details element contains it)
    expect(screen.getByText('This content is hidden by default.')).toBeInTheDocument()
  })

  it('toggles collapsible content when summary is clicked', async () => {
    const user = userEvent.setup()
    const markdown = `
<details>
<summary>Toggle me</summary>

Hidden content here.

</details>
`

    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const summary = screen.getByText('Toggle me')
    const details = container.querySelector('details')

    // Initially closed
    expect(details).not.toHaveAttribute('open')

    // Click to open
    await user.click(summary)
    expect(details).toHaveAttribute('open')

    // Click to close
    await user.click(summary)
    expect(details).not.toHaveAttribute('open')
  })

  it('renders multiple collapsible sections', () => {
    const markdown = `
# Multiple Sections

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

    render(<MarkdownPreview content={markdown} showMetadata={false} />)

    expect(screen.getByText('Section 1')).toBeInTheDocument()
    expect(screen.getByText('Section 2')).toBeInTheDocument()
    expect(screen.getByText('Section 3')).toBeInTheDocument()
  })

  it('renders code blocks inside collapsible sections', () => {
    const markdown = `
<details>
<summary>Solution</summary>

\`\`\`python
def solve():
    return 42
\`\`\`

</details>
`

    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    expect(screen.getByText('Solution')).toBeInTheDocument()

    // Code is tokenized by Prism, so check for code element
    const codeBlock = container.querySelector('code[data-testid="code-block"]')
    expect(codeBlock).toBeInTheDocument()
    expect(codeBlock?.textContent).toContain('def')
    expect(codeBlock?.textContent).toContain('solve')
  })
})

describe('MarkdownPreview - Visual Hierarchy', () => {
  it('renders horizontal rules with decorative styling', () => {
    const markdown = `
## Section 1

Content here.

---

## Section 2

More content.
`

    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const hr = container.querySelector('hr')
    expect(hr).toBeInTheDocument()
  })

  it('renders headings with proper spacing', () => {
    const markdown = `
# Title

## Subtitle

### Subheading

Content paragraph.
`

    const { container } = render(<MarkdownPreview content={markdown} showMetadata={false} />)

    const h1 = container.querySelector('h1')
    const h2 = container.querySelector('h2')
    const h3 = container.querySelector('h3')

    expect(h1).toBeInTheDocument()
    expect(h2).toBeInTheDocument()
    expect(h3).toBeInTheDocument()
  })
})
