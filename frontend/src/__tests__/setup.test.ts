import { describe, it, expect } from 'vitest'

describe('Vitest Setup', () => {
  it('should run a basic test', () => {
    expect(true).toBe(true)
  })

  it('should support TypeScript', () => {
    const sum = (a: number, b: number): number => a + b
    expect(sum(2, 3)).toBe(5)
  })
})
