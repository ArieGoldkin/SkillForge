import { useState } from 'react'

import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { LogOut } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { mockTutoringAPI } from '@services/mock.service'

import { ExitSessionDialog } from './ExitSessionDialog'

interface SessionHeaderProps {
  sessionId: string
  analysisId: string
}

export function SessionHeader({ sessionId, analysisId }: SessionHeaderProps) {
  const [showExitDialog, setShowExitDialog] = useState(false)
  const navigate = useNavigate()

  const endSessionMutation = useMutation({
    mutationFn: () => mockTutoringAPI.endSession(sessionId),
    onSuccess: () => {
      // Clear localStorage for this session
      localStorage.removeItem(`tutor-session-${sessionId}`)
      // Navigate to analysis view
      navigate({ to: '/artifact/$artifactId', params: { artifactId: analysisId } })
    },
  })

  return (
    <>
      <div className="flex items-center justify-between mb-6" data-testid="session-info">
        <div>
          <h1 className="text-3xl font-bold mb-2">Socratic Tutoring Session</h1>
          <p className="text-muted-foreground">
            Interactive learning with AI guidance - ask questions to deepen your understanding
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => setShowExitDialog(true)}
          disabled={endSessionMutation.isPending}
          data-testid="exit-tutoring-button"
        >
          <LogOut className="h-4 w-4 mr-2" />
          Exit Tutoring
        </Button>
      </div>

      <ExitSessionDialog
        open={showExitDialog}
        onOpenChange={setShowExitDialog}
        onConfirm={() => endSessionMutation.mutate()}
        isPending={endSessionMutation.isPending}
      />
    </>
  )
}
