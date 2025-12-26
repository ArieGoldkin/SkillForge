import * as React from 'react'

import { Loader2, Send } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

/**
 * Props for ChatInput component
 */
export interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
  maxLength?: number
  className?: string
}

/**
 * ChatInput - Input field for chat messages
 *
 * Auto-growing textarea with send button, character counter, and keyboard shortcuts.
 * Supports disabled state with loading indicator.
 *
 * Keyboard shortcuts:
 * - Enter: Send message
 * - Shift+Enter: New line
 *
 * @example
 * ```tsx
 * <ChatInput
 *   onSend={(message) => sendMessage(message)}
 *   disabled={isSending}
 *   placeholder="Type your message..."
 *   maxLength={2000}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires auto-grow textarea logic with useEffect, keyboard event handlers, character counter, and complete input/button layout. Further extraction would fragment cohesive input functionality. */
export function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Type your message...',
  maxLength = 2000,
  className,
}: ChatInputProps): React.ReactNode {
  const [message, setMessage] = React.useState('')
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // Auto-grow textarea
  React.useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto'

    // Calculate new height (max 5 lines ~= 120px)
    const newHeight = Math.min(textarea.scrollHeight, 120)
    textarea.style.height = `${newHeight}px`
  }, [])

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value

    // Enforce max length
    if (newValue.length <= maxLength) {
      setMessage(newValue)
    }
  }

  const handleSubmit = () => {
    const trimmedMessage = message.trim()

    if (trimmedMessage && !disabled) {
      onSend(trimmedMessage)
      setMessage('')

      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

  const isNearMaxLength = message.length > maxLength * 0.9
  const canSend = message.trim().length > 0 && !disabled

  return (
    <div className={cn('relative flex items-end gap-2', className)}>
      {/* Textarea */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'w-full resize-none rounded-lg border border-input bg-background px-4 py-3 text-sm',
            'placeholder:text-muted-foreground',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-all duration-200'
          )}
          aria-label="Message input"
          aria-describedby={isNearMaxLength ? 'char-count' : undefined}
        />

        {/* Character count */}
        {isNearMaxLength && (
          <div id="char-count" className="absolute bottom-2 right-2 text-xs text-muted-foreground">
            {message.length}/{maxLength}
          </div>
        )}
      </div>

      {/* Send button */}
      <Button
        onClick={handleSubmit}
        disabled={!canSend}
        size="icon"
        className="h-12 w-12 shrink-0"
        aria-label="Send message"
      >
        {disabled ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
      </Button>
    </div>
  )
}

ChatInput.displayName = 'ChatInput'
