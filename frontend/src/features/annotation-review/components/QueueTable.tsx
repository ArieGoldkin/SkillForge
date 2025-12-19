/**
 * Table component for displaying annotation queue items.
 * Shows artifact info, reason, status, and actions.
 */

import type { AnnotationQueueItem } from '@app-types/annotations'

import { Badge } from '@shared/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/components/ui/table'

import { QueueItemActions } from './QueueItemActions'

interface QueueTableProps {
  items: AnnotationQueueItem[]
  onMarkReviewed: (queueId: number) => void
  isMarkingReviewed: boolean
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function getStatusBadgeVariant(status: string): 'default' | 'secondary' | 'outline' {
  switch (status) {
    case 'pending':
      return 'default'
    case 'reviewed':
      return 'secondary'
    default:
      return 'outline'
  }
}

export function QueueTable({ items, onMarkReviewed, isMarkingReviewed }: QueueTableProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>No items in the review queue.</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Artifact ID</TableHead>
          <TableHead>Reason</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Reviewed</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.id}>
            <TableCell className="font-mono text-xs">{item.artifact_id.slice(0, 8)}...</TableCell>
            <TableCell className="max-w-xs truncate">{item.reason}</TableCell>
            <TableCell>
              <Badge variant={getStatusBadgeVariant(item.status)}>{item.status}</Badge>
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {formatDate(item.created_at)}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {formatDate(item.reviewed_at)}
            </TableCell>
            <TableCell className="text-right">
              <QueueItemActions
                queueId={item.id}
                artifactId={item.artifact_id}
                status={item.status}
                onMarkReviewed={onMarkReviewed}
                isMarkingReviewed={isMarkingReviewed}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
