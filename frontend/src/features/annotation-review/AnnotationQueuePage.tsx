/**
 * AnnotationQueuePage - Main page for reviewing flagged artifacts.
 * Displays annotation queue items with filtering and pagination.
 */

import { useState } from 'react'

import { RefreshCw } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@shared/components/ui/alert'
import { Button } from '@shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@shared/components/ui/card'

import { Pagination } from './components/Pagination'
import { QueueTable } from './components/QueueTable'
import { StatusFilter } from './components/StatusFilter'
import { useAnnotationQueue } from './hooks/useAnnotationQueue'

const ITEMS_PER_PAGE = 20

function QueueCardHeader({ isLoading, onRefresh }: { isLoading: boolean; onRefresh: () => void }) {
  return (
    <CardHeader>
      <div className="flex items-center justify-between">
        <div>
          <CardTitle>Annotation Review Queue</CardTitle>
          <CardDescription>Review flagged artifacts and mark them as reviewed</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
    </CardHeader>
  )
}

export default function AnnotationQueuePage() {
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'reviewed'>('pending')
  const [offset, setOffset] = useState(0)

  const { items, total, isLoading, error, refetch, markReviewed, isMarkingReviewed } =
    useAnnotationQueue({
      limit: ITEMS_PER_PAGE,
      offset,
      status: statusFilter === 'all' ? undefined : statusFilter,
    })

  const handleStatusChange = (value: 'all' | 'pending' | 'reviewed') => {
    setStatusFilter(value)
    setOffset(0)
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <Card>
        <QueueCardHeader isLoading={isLoading} onRefresh={() => refetch()} />
        <CardContent>
          <StatusFilter value={statusFilter} onChange={handleStatusChange} total={total} />
          {error && <QueueError error={error} />}
          {isLoading && <LoadingState />}
          {!isLoading && (
            <>
              <QueueTable
                items={items}
                onMarkReviewed={markReviewed}
                isMarkingReviewed={isMarkingReviewed}
              />
              <Pagination
                currentPage={Math.floor(offset / ITEMS_PER_PAGE) + 1}
                totalPages={Math.ceil(total / ITEMS_PER_PAGE)}
                hasPrevPage={offset > 0}
                hasNextPage={offset + ITEMS_PER_PAGE < total}
                onPrevPage={() => setOffset(Math.max(0, offset - ITEMS_PER_PAGE))}
                onNextPage={() => setOffset(offset + ITEMS_PER_PAGE)}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function QueueError({ error }: { error: Error | null }) {
  if (!error) return null
  return (
    <Alert variant="destructive" className="mb-6">
      <AlertTitle>Error loading queue</AlertTitle>
      <AlertDescription>
        {error instanceof Error ? error.message : 'An error occurred while loading the queue'}
      </AlertDescription>
    </Alert>
  )
}

function LoadingState() {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p>Loading annotation queue...</p>
    </div>
  )
}
