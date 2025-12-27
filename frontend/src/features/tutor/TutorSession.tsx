/**
 * TutorSession - Interactive tutoring chat with React 19 optimistic updates
 *
 * Uses useTutorChat hook for instant message display:
 * - User messages appear immediately (before API response)
 * - Automatic rollback on failure
 * - No prop drilling between hooks
 */

import { useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'

import { mockTutoringAPI } from '@services/mock.service'

import { InputArea } from './components/InputArea'
import { LoadingState } from './components/LoadingState'
import { MessagesArea } from './components/MessagesArea'
import { NotFoundState } from './components/NotFoundState'
import { SessionHeader } from './components/SessionHeader'
import { useTutorChat } from './hooks/useTutorChat'

export default function TutorSession() {
  const { sessionId } = useParams({ from: '/tutor/$sessionId' })

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ['tutoring-session', sessionId],
    queryFn: () => mockTutoringAPI.getSession(sessionId),
  })

  // React 19 unified hook - handles fetching, sending, and optimistic updates
  const {
    messages,
    sendMessage,
    isPending,
    isLoading: messagesLoading,
  } = useTutorChat({ sessionId })

  if (sessionLoading || messagesLoading) return <LoadingState />
  if (!session) return <NotFoundState />

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <SessionHeader sessionId={sessionId} analysisId={session.analysis_id} />
      <div className="bg-card border rounded-xl flex flex-col h-[600px]">
        <MessagesArea messages={messages} isPending={isPending} />
        <InputArea onSend={sendMessage} disabled={isPending} />
      </div>
    </div>
  )
}
