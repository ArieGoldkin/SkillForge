/**
 * Pagination controls for annotation queue.
 */

import { Button } from '@shared/components/ui/button'

interface PaginationProps {
  currentPage: number
  totalPages: number
  hasPrevPage: boolean
  hasNextPage: boolean
  onPrevPage: () => void
  onNextPage: () => void
}

export function Pagination({
  currentPage,
  totalPages,
  hasPrevPage,
  hasNextPage,
  onPrevPage,
  onNextPage,
}: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className="mt-6 flex items-center justify-between">
      <div className="text-sm text-muted-foreground">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onPrevPage} disabled={!hasPrevPage}>
          Previous
        </Button>
        <Button variant="outline" size="sm" onClick={onNextPage} disabled={!hasNextPage}>
          Next
        </Button>
      </div>
    </div>
  )
}
