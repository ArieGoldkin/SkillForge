import { useEffect, useRef } from 'react'

import type { TutoringMessage } from '@app-types/api'

import { ChatMessage } from './ChatMessage'

interface MessagesAreaProps {
  messages: TutoringMessage[]
  isPending: boolean
}

export function MessagesArea({ messages, isPending }: MessagesAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change or typing indicator appears
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isPending])

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4" data-testid="message-list">
      {messages.map((message) => (
        <ChatMessage
          key={message.id}
          role={message.role}
          content={message.content}
          timestamp={new Date(message.created_at)}
        />
      ))}
      {isPending && (
        <div
          className="flex items-center gap-2 text-muted-foreground text-sm"
          data-testid="typing-indicator"
        >
          <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          <span>Thinking...</span>
        </div>
      )}
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  )
}
