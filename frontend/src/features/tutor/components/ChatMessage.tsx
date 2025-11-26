import type * as React from 'react'

import { Bot, User } from 'lucide-react'

import { cn } from '@lib/utils'

/**
 * Message role type
 */
export type MessageRole = 'user' | 'assistant'

/**
 * Props for ChatMessage component
 */
export interface ChatMessageProps {
  role: MessageRole
  content: string
  timestamp: Date
  isStreaming?: boolean
  className?: string
}

/**
 * Format timestamp to time string
 */
const formatTimestamp = (timestamp: Date): string => {
  return timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Streaming cursor animation
 */
const StreamingCursor: React.FC = () => {
  return (
    <span className="inline-block w-1 h-4 ml-0.5 bg-current animate-pulse" aria-hidden="true" />
  )
}

/**
 * ChatMessage - Message bubble for user/assistant chat
 *
 * Displays a chat message with role-specific styling, avatar, and timestamp.
 * Supports streaming indicator for real-time message generation.
 *
 * Design:
 * - User messages: Right-aligned with teal background
 * - Assistant messages: Left-aligned with muted background
 * - Avatar icons for visual distinction
 * - Timestamp below message
 * - Markdown support ready (content can be pre-processed)
 *
 * @example
 * ```tsx
 * <ChatMessage
 *   role="assistant"
 *   content="Hello! How can I help you today?"
 *   timestamp={new Date()}
 * />
 *
 * <ChatMessage
 *   role="user"
 *   content="I need help with React Server Components"
 *   timestamp={new Date()}
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Component requires complete chat bubble layout with role-based styling, avatar, content, timestamp, and streaming indicator. Already well-structured with extracted StreamingCursor sub-component. */
export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  timestamp,
  isStreaming = false,
  className,
}) => {
  const isUser = role === 'user'

  return (
    <div
      className={cn(
        'flex gap-3 animate-in slide-in-from-bottom-2 duration-300',
        isUser ? 'flex-row-reverse' : 'flex-row',
        className
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
        )}
        aria-label={isUser ? 'User' : 'Assistant'}
      >
        {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
      </div>

      {/* Message content */}
      <div
        className={cn(
          'flex flex-col gap-1 max-w-[80%] md:max-w-[90%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Message bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3 wrap-break-word',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm'
          )}
        >
          {/* Content with proper whitespace handling */}
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {content}
            {isStreaming && <StreamingCursor />}
          </div>
        </div>

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">{formatTimestamp(timestamp)}</span>
      </div>
    </div>
  )
}

ChatMessage.displayName = 'ChatMessage'
