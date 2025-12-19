/**
 * Test Factory Utilities - Barrel Export
 *
 * Centralized exports for all test factory functions.
 * These factories provide type-safe alternatives to `{} as any`
 * when creating mock objects in tests.
 *
 * @module test-utils/factories
 */

export { createMockInfiniteQueryResult } from './queryResultFactory'
export { createTestSSEProgressEvent } from './sseEventFactory'
export { createMockAnchorElement } from './domMockFactory'
