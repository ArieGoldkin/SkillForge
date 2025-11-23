import { useParams } from '@tanstack/react-router'

export default function TutorSession() {
  // TanStack Router provides type-safe params automatically
  const { sessionId } = useParams({ from: '/tutor/$sessionId' })

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Socratic Tutoring Session</h1>
      <p className="text-muted-foreground mb-4">Session ID: {sessionId}</p>
      <div className="space-y-4">
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Interactive Learning</h2>
          <p className="text-muted-foreground">
            Socratic dialogue for implementation guidance will appear here
          </p>
        </div>
      </div>
    </div>
  )
}
