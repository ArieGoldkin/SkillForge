import { ChatInput } from '@/shared/components/features/tutor/ChatInput'

interface InputAreaProps {
  onSend: (content: string) => void
  disabled: boolean
}

export function InputArea({ onSend, disabled }: InputAreaProps) {
  return (
    <div className="border-t p-4">
      <ChatInput
        onSend={onSend}
        disabled={disabled}
        placeholder="Ask a question or share your thoughts..."
      />
    </div>
  )
}
