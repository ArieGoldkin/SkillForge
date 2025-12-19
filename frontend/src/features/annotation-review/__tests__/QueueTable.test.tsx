/**
 * Tests for QueueTable component - Displays annotation queue items in a table
 */

import type { ReactNode } from 'react'

import type { AnnotationQueueItem } from '@app-types/annotations'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { QueueTable } from '../components/QueueTable'

// Mock TanStack Router Link component
vi.mock('@tanstack/react-router', () => ({
  Link: ({
    to,
    params,
    children,
    className,
  }: {
    to: string
    params: { artifactId: string }
    children: ReactNode
    className?: string
  }) => (
    <a href={`${to.replace('$artifactId', params.artifactId)}`} className={className}>
      {children}
    </a>
  ),
}))

describe('QueueTable', () => {
  const mockOnMarkReviewed = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Empty state', () => {
    it('shows empty message when no items', () => {
      render(
        <QueueTable items={[]} onMarkReviewed={mockOnMarkReviewed} isMarkingReviewed={false} />
      )

      expect(screen.getByText('No items in the review queue.')).toBeInTheDocument()
    })

    it('does not show table headers when empty', () => {
      render(
        <QueueTable items={[]} onMarkReviewed={mockOnMarkReviewed} isMarkingReviewed={false} />
      )

      expect(screen.queryByRole('columnheader', { name: /artifact id/i })).not.toBeInTheDocument()
    })
  })

  describe('Table rendering', () => {
    it('renders table headers', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test reason',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      expect(screen.getByText('Artifact ID')).toBeInTheDocument()
      expect(screen.getByText('Reason')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Created')).toBeInTheDocument()
      expect(screen.getByText('Reviewed')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('renders all queue items', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Poor quality',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
        {
          id: 2,
          artifact_id: 'artifact-456',
          reason: 'Incorrect info',
          status: 'reviewed',
          created_at: '2024-01-02T10:00:00Z',
          reviewed_at: '2024-01-02T11:00:00Z',
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      expect(screen.getByText('Poor quality')).toBeInTheDocument()
      expect(screen.getByText('Incorrect info')).toBeInTheDocument()
    })

    it('truncates artifact ID to first 8 characters', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123456789-very-long',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      // Should show first 8 chars + "..." = "artifact..."
      expect(screen.getByText(/artifact\.\.\./i)).toBeInTheDocument()
    })
  })

  describe('Status badges', () => {
    it('shows pending badge for pending items', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      const badge = screen.getByText('pending')
      expect(badge).toBeInTheDocument()
    })

    it('shows reviewed badge for reviewed items', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'reviewed',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: '2024-01-01T11:00:00Z',
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      const badge = screen.getByText('reviewed')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('Date formatting', () => {
    it('formats created_at date correctly', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-15T14:30:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      // Date format: "Jan 15, 2024, 02:30 PM" (or similar depending on locale)
      expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument()
    })

    it('shows N/A for null reviewed_at date', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      const cells = screen.getAllByText('N/A')
      expect(cells.length).toBeGreaterThan(0)
    })

    it('formats reviewed_at date when present', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'reviewed',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: '2024-01-15T16:45:00Z',
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument()
    })
  })

  describe('Actions column', () => {
    it('renders view artifact link', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', '/artifact/artifact-123')
    })

    it('renders mark reviewed button for pending items', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      expect(screen.getByRole('button', { name: /mark reviewed/i })).toBeInTheDocument()
    })

    it('shows reviewed button as disabled for reviewed items', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Test',
          status: 'reviewed',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: '2024-01-01T11:00:00Z',
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      const button = screen.getByRole('button', { name: /reviewed/i })
      expect(button).toBeDisabled()
    })
  })

  describe('Reason truncation', () => {
    it('truncates long reasons with ellipsis', () => {
      const longReason = 'This is a very long reason that should be truncated '.repeat(5)
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: longReason,
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
      ]

      const { container } = render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      // Check that the cell has truncate class
      const reasonCell = container.querySelector('.truncate')
      expect(reasonCell).toBeInTheDocument()
      expect(reasonCell?.textContent).toBe(longReason)
    })
  })

  describe('Multiple rows', () => {
    it('renders multiple rows with unique keys', () => {
      const mockItems: AnnotationQueueItem[] = [
        {
          id: 1,
          artifact_id: 'artifact-123',
          reason: 'Reason 1',
          status: 'pending',
          created_at: '2024-01-01T10:00:00Z',
          reviewed_at: null,
        },
        {
          id: 2,
          artifact_id: 'artifact-456',
          reason: 'Reason 2',
          status: 'pending',
          created_at: '2024-01-02T10:00:00Z',
          reviewed_at: null,
        },
        {
          id: 3,
          artifact_id: 'artifact-789',
          reason: 'Reason 3',
          status: 'reviewed',
          created_at: '2024-01-03T10:00:00Z',
          reviewed_at: '2024-01-03T11:00:00Z',
        },
      ]

      render(
        <QueueTable
          items={mockItems}
          onMarkReviewed={mockOnMarkReviewed}
          isMarkingReviewed={false}
        />
      )

      expect(screen.getByText('Reason 1')).toBeInTheDocument()
      expect(screen.getByText('Reason 2')).toBeInTheDocument()
      expect(screen.getByText('Reason 3')).toBeInTheDocument()

      // Should have 3 rows (excluding header)
      const rows = screen.getAllByRole('row')
      expect(rows).toHaveLength(4) // 1 header + 3 data rows
    })
  })
})
