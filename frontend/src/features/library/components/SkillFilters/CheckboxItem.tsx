/**
 * CheckboxItem - Reusable checkbox component for filters
 */

import type * as React from 'react'

/**
 * Props for CheckboxItem component
 */
export interface CheckboxItemProps {
  id: string
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  type?: 'checkbox' | 'radio'
  name?: string
}

/**
 * CheckboxItem component
 *
 * Styled checkbox with label for filter sections.
 * Provides hover effects and keyboard accessibility.
 */
export function CheckboxItem({
  id,
  label,
  checked,
  onChange,
  type = 'checkbox',
  name,
}: CheckboxItemProps): React.ReactNode {
  return (
    <label
      htmlFor={id}
      className="flex items-center gap-2 py-2 px-3 rounded-md hover:bg-accent cursor-pointer transition-colors"
    >
      <input
        type={type}
        id={id}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-border text-primary focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer"
        name={name}
      />
      <span className="text-sm capitalize">{label}</span>
    </label>
  )
}

CheckboxItem.displayName = 'CheckboxItem'
