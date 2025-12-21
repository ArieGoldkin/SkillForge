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
