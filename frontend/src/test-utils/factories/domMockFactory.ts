/**
 * DOM Mock Factory for Testing
 *
 * Provides type-safe factory functions for creating mock DOM elements
 * in tests, particularly useful for document.createElement mocks.
 *
 * @module test-utils/factories/domMockFactory
 */

import { vi } from 'vitest'

/**
 * Create a type-safe mock HTMLAnchorElement
 *
 * Commonly used when testing download functionality or link manipulation
 * that relies on creating anchor elements programmatically.
 *
 * @example
 * ```typescript
 * // Mock document.createElement for download tests
 * vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
 *   if (tagName === 'a') {
 *     return createMockAnchorElement({
 *       href: '',
 *       download: ''
 *     })
 *   }
 *   return document.createElement(tagName)
 * })
 * ```
 *
 * @param overrides - Partial anchor element properties to override defaults
 * @returns Fully typed mock HTMLAnchorElement
 */
// eslint-disable-next-line max-lines-per-function -- Factory needs all properties for type safety
export function createMockAnchorElement(
  overrides: Partial<HTMLAnchorElement> = {}
): HTMLAnchorElement {
  // Filter out undefined values from overrides to prevent overwriting defaults
  const filteredOverrides = Object.entries(overrides).reduce(
    (acc, [key, value]) => {
      if (value !== undefined) {
        acc[key as keyof HTMLAnchorElement] = value
      }
      return acc
    },
    {} as Partial<HTMLAnchorElement>
  )

  // Create base defaults
  const defaults = {
    // Core anchor properties
    href: '',
    download: '',
    target: '',
    rel: '',
    text: '',

    // Common DOM element properties
    tagName: 'A',
    nodeName: 'A',
    nodeType: 1, // ELEMENT_NODE

    // Methods
    click: vi.fn(),
    setAttribute: vi.fn(),
    getAttribute: vi.fn(),
    removeAttribute: vi.fn(),
    hasAttribute: vi.fn(),

    // DOM manipulation methods
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),

    // Parent/child relationships
    appendChild: vi.fn(),
    removeChild: vi.fn(),
    parentNode: null,
    parentElement: null,
    childNodes: [] as unknown as NodeListOf<ChildNode>,
    children: [] as unknown as HTMLCollection,

    // Style and classes
    className: '',
    classList: {
      add: vi.fn(),
      remove: vi.fn(),
      toggle: vi.fn(),
      contains: vi.fn(),
    },
    style: {} as CSSStyleDeclaration,

    // Common utility methods
    cloneNode: vi.fn(),
    contains: vi.fn(),
  }

  // Merge filtered overrides with defaults
  // Note: We return the object directly without type assertion to preserve properties
  return {
    ...defaults,
    ...filteredOverrides,
  } as HTMLAnchorElement
}
