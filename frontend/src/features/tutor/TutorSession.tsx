import { useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'

import { mockTutoringAPI } from '@services/mock.service'

import { InputArea } from './components/InputArea'
import { LoadingState } from './components/LoadingState'
import { MessagesArea } from './components/MessagesArea'
import { NotFoundState } from './components/NotFoundState'
import { SessionHeader } from './components/SessionHeader'
import { useSendMessage } from './hooks/useSendMessage'
import { useTutoringMessages } from './hooks/useTutoringMessages'

export default function TutorSession() {
  const { sessionId } = useParams({ from: '/tutor/$sessionId' })

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ['tutoring-session', sessionId],
    queryFn: () => mockTutoringAPI.getSession(sessionId),
  })

  const { messages, setMessages, isLoading: messagesLoading } = useTutoringMessages(sessionId)

  const sendMessageMutation = useSendMessage({
    sessionId,
    messages,
    setMessages,
  })

  if (sessionLoading || messagesLoading) return <LoadingState />
  if (!session) return <NotFoundState />

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <SessionHeader sessionId={sessionId} analysisId={session.analysis_id} />
      <div className="bg-card border rounded-xl flex flex-col h-[600px]">
        <MessagesArea messages={messages} isPending={sendMessageMutation.isPending} />
        <InputArea
          onSend={(content) => sendMessageMutation.mutate(content)}
          disabled={sendMessageMutation.isPending}
        />
      </div>
    </div>
  )
}
