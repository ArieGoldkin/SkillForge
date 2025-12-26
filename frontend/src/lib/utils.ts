import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Shallow equality check for objects
 * Compares all enumerable properties shallowly (===)
 *
 * Used to prevent unnecessary re-renders by detecting when object values haven't changed
 * despite having a new reference.
 *
 * @param a - First object to compare
 * @param b - Second object to compare
 * @returns true if all properties are equal (===), false otherwise
 */
export function shallowEqual<T extends Record<string, unknown>>(a: T, b: T): boolean {
  const aKeys = Object.keys(a) as Array<keyof T>
  const bKeys = Object.keys(b) as Array<keyof T>

  if (aKeys.length !== bKeys.length) return false

  return aKeys.every((key) => a[key] === b[key])
}

/**
 * Exhaustive type checking helper for discriminated unions
 *
 * Issue #549: Add exhaustive type checking for discriminated unions
 *
 * Use this in the default case of switch statements on discriminated unions.
 * TypeScript will error at compile time if any case is unhandled.
 *
 * @example
 * ```typescript
 * type Status = 'pending' | 'running' | 'complete'
 *
 * function handleStatus(status: Status): string {
 *   switch (status) {
 *     case 'pending': return 'Waiting...'
 *     case 'running': return 'In progress...'
 *     case 'complete': return 'Done!'
 *     default: return assertNever(status) // TS error if case missed
 *   }
 * }
 * ```
 *
 * @param value - The value that should never be reached
 * @param message - Optional custom error message
 * @throws Error at runtime if somehow reached (type system bypassed)
 */
export function assertNever(value: never, message?: string): never {
  throw new Error(message ?? `Unexpected value: ${JSON.stringify(value)}`)
}

/**
 * Non-throwing version for cases where you want to handle unknown values gracefully
 * Logs a warning but returns undefined instead of throwing
 *
 * @example
 * ```typescript
 * switch (status) {
 *   case 'pending': return 'Waiting...'
 *   case 'running': return 'In progress...'
 *   default:
 *     assertNeverSoft(status, 'Unknown status') // Logs warning
 *     return 'Unknown'
 * }
 * ```
 */
export function assertNeverSoft(value: never, context?: string): void {
  console.warn(
    `[assertNever] Unhandled value${context ? ` in ${context}` : ''}: ${JSON.stringify(value)}`
  )
}
