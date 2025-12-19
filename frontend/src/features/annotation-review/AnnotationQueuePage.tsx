/**
 * AnnotationQueuePage - Main page for reviewing flagged artifacts
 *
 * Displays a table of annotation queue items with filtering and pagination.
 * Allows reviewers to view artifacts and mark items as reviewed.
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
import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

import { QueueTable } from './components/QueueTable'
import { useAnnotationQueue } from './hooks/useAnnotationQueue'

export default function AnnotationQueuePage() {
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'reviewed'>('pending')
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { items, total, isLoading, error, refetch, markReviewed, isMarkingReviewed } =
    useAnnotationQueue({
      limit,
      offset,
      status: statusFilter === 'all' ? undefined : statusFilter,
    })

  const handleStatusChange = (value: string) => {
    setStatusFilter(value as 'all' | 'pending' | 'reviewed')
    setOffset(0) // Reset to first page when filter changes
  }

  const handlePrevPage = () => {
    setOffset(Math.max(0, offset - limit))
  }

  const handleNextPage = () => {
    if (offset + limit < total) {
      setOffset(offset + limit)
    }
  }

  const currentPage = Math.floor(offset / limit) + 1
  const totalPages = Math.ceil(total / limit)
  const hasNextPage = offset + limit < total
  const hasPrevPage = offset > 0

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Annotation Review Queue</CardTitle>
              <CardDescription>Review flagged artifacts and mark them as reviewed</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {/* Status Filter */}
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Tabs value={statusFilter} onValueChange={handleStatusChange}>
                <TabsList>
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="pending">Pending</TabsTrigger>
                  <TabsTrigger value="reviewed">Reviewed</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            <span className="text-sm text-muted-foreground">
              {total} total item{total === 1 ? '' : 's'}
            </span>
          </div>

          {/* Error State */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertTitle>Error loading queue</AlertTitle>
              <AlertDescription>
                {error instanceof Error
                  ? error.message
                  : 'An error occurred while loading the queue'}
              </AlertDescription>
            </Alert>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12 text-muted-foreground">
              <p>Loading annotation queue...</p>
            </div>
          )}

          {/* Queue Table */}
          {!isLoading && (
            <>
              <QueueTable
                items={items}
                onMarkReviewed={markReviewed}
                isMarkingReviewed={isMarkingReviewed}
              />

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6 flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePrevPage}
                      disabled={!hasPrevPage}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={!hasNextPage}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
