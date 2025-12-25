/**
 * Reusable submit button component that uses React 19 useFormStatus
 * to automatically detect form submission state.
 */

import { useFormStatus } from 'react-dom'

import { Button } from '@shared/components/ui/button'
import type { ButtonProps } from '@shared/components/ui/button'

interface SubmitButtonProps extends Omit<ButtonProps, 'type' | 'disabled'> {
  loadingText?: string
  idleText?: string
}

export function SubmitButton({
  loadingText = 'Submitting...',
  idleText = 'Submit',
  children,
  ...props
}: SubmitButtonProps) {
  const { pending } = useFormStatus()

  return (
    <Button type="submit" disabled={pending} aria-busy={pending} {...props}>
      {pending ? loadingText : children || idleText}
    </Button>
  )
}
