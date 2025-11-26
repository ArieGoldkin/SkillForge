import { type ErrorComponentProps, useRouter } from '@tanstack/react-router'

import { Button } from '@shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

export function GlobalErrorComponent({ error }: ErrorComponentProps) {
  const router = useRouter()

  const handleReset = () => {
    router.invalidate()
  }

  const handleGoHome = () => {
    router.navigate({ to: '/' })
  }

  const isDev = import.meta.env.DEV

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-destructive">Navigation Error</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {error.message || 'An error occurred while navigating to this page.'}
          </p>
          {isDev && error.stack && (
            <pre className="mt-2 overflow-auto rounded bg-muted p-2 text-xs">{error.stack}</pre>
          )}
          <div className="flex gap-2">
            <Button variant="teal" onClick={handleReset}>
              Try Again
            </Button>
            <Button variant="outline" onClick={handleGoHome}>
              Return to Home
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
