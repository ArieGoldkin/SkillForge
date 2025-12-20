import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MarkdownPreview } from '../index'

describe('MarkdownPreview - Table Rendering', () => {
  it('should render GFM tables with proper HTML structure', () => {
    const markdownWithTable = `
# Test Document

Here's a table:

| Term | Definition |
|------|------------|
| Chain-of-Thought (CoT) | A prompting technique that encourages LLMs to show their reasoning |
| Few-Shot Learning | Providing examples in the prompt to guide the model |
| Zero-Shot | Asking the model to perform a task without examples |
`

    render(<MarkdownPreview content={markdownWithTable} showMetadata={false} />)

    // Check that table wrapper exists
    const tableWrapper = document.querySelector('.table-wrapper')
    expect(tableWrapper).toBeInTheDocument()

    // Check that table element exists
    const table = document.querySelector('table')
    expect(table).toBeInTheDocument()

    // Check that thead exists
    const thead = document.querySelector('thead')
    expect(thead).toBeInTheDocument()

    // Check that tbody exists
    const tbody = document.querySelector('tbody')
    expect(tbody).toBeInTheDocument()

    // Check that header cells exist
    const headerCells = document.querySelectorAll('th')
    expect(headerCells).toHaveLength(2)
    expect(headerCells[0]).toHaveTextContent('Term')
    expect(headerCells[1]).toHaveTextContent('Definition')

    // Check that data rows exist
    const dataRows = document.querySelectorAll('tbody tr')
    expect(dataRows).toHaveLength(3)

    // Check first row data
    const firstRowCells = dataRows[0].querySelectorAll('td')
    expect(firstRowCells[0]).toHaveTextContent('Chain-of-Thought (CoT)')
    expect(firstRowCells[1]).toHaveTextContent(
      'A prompting technique that encourages LLMs to show their reasoning'
    )
  })

  it('should render tables with different column counts', () => {
    const markdownWithWideTable = `
| Col 1 | Col 2 | Col 3 | Col 4 |
|-------|-------|-------|-------|
| A1    | B1    | C1    | D1    |
| A2    | B2    | C2    | D2    |
`

    render(<MarkdownPreview content={markdownWithWideTable} showMetadata={false} />)

    const headerCells = document.querySelectorAll('th')
    expect(headerCells).toHaveLength(4)

    const firstRowCells = document.querySelectorAll('tbody tr:first-child td')
    expect(firstRowCells).toHaveLength(4)
  })

  it('should render tables with inline formatting', () => {
    const markdownWithFormatting = `
| Feature | Status |
|---------|--------|
| **Bold** | \`code\` |
| *Italic* | [Link](https://example.com) |
`

    render(<MarkdownPreview content={markdownWithFormatting} showMetadata={false} />)

    // Check that bold text is rendered
    const bold = document.querySelector('td strong')
    expect(bold).toHaveTextContent('Bold')

    // Check that inline code is rendered
    const code = document.querySelector('td code')
    expect(code).toHaveTextContent('code')

    // Check that italic is rendered
    const italic = document.querySelector('td em')
    expect(italic).toHaveTextContent('Italic')

    // Check that link is rendered
    const link = document.querySelector('td a')
    expect(link).toHaveTextContent('Link')
    expect(link).toHaveAttribute('href', 'https://example.com')
  })

  it('should apply proper CSS classes for styling', () => {
    const markdown = `
| Header 1 | Header 2 |
|----------|----------|
| Data 1   | Data 2   |
`

    render(<MarkdownPreview content={markdown} showMetadata={false} />)

    // Table wrapper should have the class for overflow handling
    const tableWrapper = document.querySelector('.table-wrapper')
    expect(tableWrapper).toBeInTheDocument()
    expect(tableWrapper?.firstChild?.nodeName).toBe('TABLE')
  })

  it('should handle empty cells', () => {
    const markdownWithEmptyCells = `
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  |          | Value 3  |
|          | Value 2  |          |
`

    render(<MarkdownPreview content={markdownWithEmptyCells} showMetadata={false} />)

    const rows = document.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(2)

    // First row should have one empty cell
    const firstRowCells = rows[0].querySelectorAll('td')
    expect(firstRowCells).toHaveLength(3)
    expect(firstRowCells[1]).toHaveTextContent('')

    // Second row should have two empty cells
    const secondRowCells = rows[1].querySelectorAll('td')
    expect(secondRowCells).toHaveLength(3)
    expect(secondRowCells[0]).toHaveTextContent('')
    expect(secondRowCells[2]).toHaveTextContent('')
  })

  it('should render multiple tables in the same document', () => {
    const markdownWithMultipleTables = `
# First Table

| A | B |
|---|---|
| 1 | 2 |

# Second Table

| C | D |
|---|---|
| 3 | 4 |
`

    render(<MarkdownPreview content={markdownWithMultipleTables} showMetadata={false} />)

    const tables = document.querySelectorAll('table')
    expect(tables).toHaveLength(2)

    const tableWrappers = document.querySelectorAll('.table-wrapper')
    expect(tableWrappers).toHaveLength(2)
  })
})
