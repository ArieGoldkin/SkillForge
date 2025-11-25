import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

// Simple test component
function TestComponent({ message }: { message: string }) {
  return (
    <div>
      <h1>Test Component</h1>
      <p>{message}</p>
    </div>
  )
}

describe('React Testing Library Setup', () => {
  it('should render a component', () => {
    render(<TestComponent message="Hello, Vitest!" />)

    expect(screen.getByText('Test Component')).toBeInTheDocument()
    expect(screen.getByText('Hello, Vitest!')).toBeInTheDocument()
  })

  it('should support @testing-library/jest-dom matchers', () => {
    render(<TestComponent message="Testing matchers" />)

    const heading = screen.getByText('Test Component')
    expect(heading).toBeVisible()
    expect(heading.tagName).toBe('H1')
  })
})
