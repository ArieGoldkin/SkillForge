import { Link } from '@tanstack/react-router'
import { FileQuestion } from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader } from '@/shared/components/ui/card'

export default function NotFound() {
  return (
    <div className="container mx-auto flex min-h-[calc(100vh-4rem)] items-center justify-center p-4">
      <Card className="w-full max-w-md text-center">
        <CardHeader className="pb-4">
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-muted">
            <FileQuestion className="h-10 w-10 text-muted-foreground" />
          </div>
          <h1 className="text-3xl font-bold">Page Not Found</h1>
          <p className="text-muted-foreground">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <p className="text-sm font-medium">You might want to visit:</p>
            <div className="flex flex-col gap-2">
              <Link to="/">
                <Button variant="outline" className="w-full">
                  Home
                </Button>
              </Link>
              <Link to="/library">
                <Button variant="outline" className="w-full">
                  Library
                </Button>
              </Link>
              <Link to="/showcase">
                <Button variant="outline" className="w-full">
                  Showcase
                </Button>
              </Link>
            </div>
          </div>
          <Link to="/">
            <Button variant="teal" className="w-full">
              Return to Home
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
