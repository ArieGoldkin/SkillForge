/**
 * Tests for CompactGroupCard - Grid-friendly card for stage group display
 *
 * Tests cover:
 * - Progress bar colors based on completion and failure states
 * - Card border colors matching group status
 * - Stage chip rendering
 * - Status summary display
 * - Accessibility compliance
 */

import { render, screen } from '@testing-library/react'
import { FileCode } from 'lucide-react'
import { describe, expect, it } from 'vitest'

import type { StageName } from '@/schemas/base'

import type { StageStatusEntry } from '../../../hooks/stageConfig'
import type { GroupStatusMeta, StageGroup } from '../../../types/accordion'
import { CompactGroupCard } from '../CompactGroupCard'

// ============================================================================
// Test Fixtures
// ============================================================================

const createMockStageStatuses = (
  statuses: Array<[StageName, StageStatusEntry['status']]>
): Map<StageName, StageStatusEntry> => {
  const map = new Map<StageName, StageStatusEntry>()
  statuses.forEach(([name, status]) => {
    map.set(name, { name, status })
  })
  return map
}

const mockGroup: StageGroup = {
  id: 'test-group',
  label: 'Test Group',
  icon: FileCode,
  stages: ['stage_1', 'stage_2', 'stage_3', 'stage_4'] as StageName[],
  description: 'Test group description',
}

// ============================================================================
// Tests
// ============================================================================

describe('CompactGroupCard', () => {
  describe('progress bar colors', () => {
    it('shows gray/empty progress bar when 0% complete', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      // Progress bar should exist with 0% value
      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toBeInTheDocument()
      expect(progressBar).toHaveAttribute('aria-valuenow', '0')
      expect(progressBar).toHaveAttribute('aria-valuetext', '0% complete')
    })

    it('shows green progress bar when 100% complete with no failures', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'completed',
        completed: 4,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 100,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'complete'],
        ['stage_4', 'complete'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '100')
      expect(progressBar).toHaveAttribute('aria-valuetext', '100% complete')
    })

    it('shows amber progress bar when there are failures', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'partial',
        completed: 2,
        failed: 2,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'failed'],
        ['stage_4', 'failed'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')

      // Check that failed stages indicator is shown
      expect(screen.getByText(/2 failed/i)).toBeInTheDocument()
    })

    it('shows red progress bar when all stages failed', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'failed',
        completed: 0,
        failed: 4,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'failed'],
        ['stage_2', 'failed'],
        ['stage_3', 'failed'],
        ['stage_4', 'failed'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '0')

      // Check that failed stages indicator is shown
      expect(screen.getByText(/4 failed/i)).toBeInTheDocument()
    })

    it('shows in-progress state with running stages', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 2,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 2,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'running'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const progressBar = screen.getByRole('progressbar')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')

      // Check that running stages indicator is shown
      expect(screen.getByText(/2 running/i)).toBeInTheDocument()
    })
  })

  describe('card border color', () => {
    it('has gray border for pending groups', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const card = container.querySelector('article')
      expect(card).toHaveClass('border-l-muted-foreground/30')
    })

    it('has green border for fully complete groups', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'completed',
        completed: 4,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 100,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'complete'],
        ['stage_4', 'complete'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const card = container.querySelector('article')
      expect(card).toHaveClass('border-l-[oklch(0.6959_0.1491_162.4796)]')
    })

    it('has amber border for groups with failures', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'partial',
        completed: 2,
        failed: 2,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'failed'],
        ['stage_4', 'failed'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const card = container.querySelector('article')
      expect(card).toHaveClass('border-l-[oklch(0.7686_0.1647_70.0804)]')
    })

    it('has gray border for fully failed groups (0% completion takes precedence)', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'failed',
        completed: 0,
        failed: 4,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'failed'],
        ['stage_2', 'failed'],
        ['stage_3', 'failed'],
        ['stage_4', 'failed'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const card = container.querySelector('article')
      // When completed=0 and running=0, uses gray border (takes precedence over failed>0)
      expect(card).toHaveClass('border-l-muted-foreground/30')
    })

    it('has blue border for in-progress groups', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 1,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 1,
        progress: 25,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'running'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const card = container.querySelector('article')
      expect(card).toHaveClass('border-l-primary')
    })
  })

  describe('stage chips', () => {
    it('renders all stage chips for group stages', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 2,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 1,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'running'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      // All 4 stage chips should be rendered
      expect(screen.getByText(/Stage 1/i)).toBeInTheDocument()
      expect(screen.getByText(/Stage 2/i)).toBeInTheDocument()
      expect(screen.getByText(/Stage 3/i)).toBeInTheDocument()
      expect(screen.getByText(/Stage 4/i)).toBeInTheDocument()
    })

    it('renders stage chips with correct aria-label attributes', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'completed',
        completed: 2,
        failed: 0,
        total: 2,
        skipped: 0,
        running: 0,
        progress: 100,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
      ])

      const smallGroup: StageGroup = {
        id: 'small-group',
        label: 'Small Group',
        icon: FileCode,
        stages: ['stage_1', 'stage_2'] as StageName[],
      }

      render(
        <CompactGroupCard
          group={smallGroup}
          statusMeta={statusMeta}
          stageStatuses={stageStatuses}
        />
      )

      // Stage chips should have accessible labels
      expect(screen.getByLabelText(/Stage 1: complete/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Stage 2: complete/i)).toBeInTheDocument()
    })
  })

  describe('status summary', () => {
    it('shows running count when stages are running', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 1,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 2,
        progress: 25,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'running'],
        ['stage_3', 'running'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.getByText(/2 running/i)).toBeInTheDocument()
      expect(screen.getByText(/1 done/i)).toBeInTheDocument()
    })

    it('shows failed count when stages have failed', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'partial',
        completed: 1,
        failed: 2,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 25,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'failed'],
        ['stage_3', 'failed'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.getByText(/2 failed/i)).toBeInTheDocument()
      expect(screen.getByText(/1 done/i)).toBeInTheDocument()
    })

    it('does not show status summary for pending groups', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.queryByText(/running/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/failed/i)).not.toBeInTheDocument()
    })

    it('hides done count when status is completed', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'completed',
        completed: 4,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 100,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'complete'],
        ['stage_4', 'complete'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      // Should not show "4 done" when status is completed
      expect(screen.queryByText(/done/i)).not.toBeInTheDocument()
    })
  })

  describe('group metadata display', () => {
    it('displays group label and icon', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.getByText('Test Group')).toBeInTheDocument()
    })

    it('displays group description when present', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.getByText('Test group description')).toBeInTheDocument()
    })

    it('does not render description when not present', () => {
      const groupWithoutDesc: StageGroup = {
        ...mockGroup,
        description: undefined,
      }
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      const { container } = render(
        <CompactGroupCard
          group={groupWithoutDesc}
          statusMeta={statusMeta}
          stageStatuses={stageStatuses}
        />
      )

      // Description paragraph should not exist
      const description = container.querySelector('p.text-muted-foreground\\/80')
      expect(description).not.toBeInTheDocument()
    })

    it('displays status badge with completed/total count', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 2,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 1,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'running'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      expect(screen.getByText('2/4')).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('has accessible article label with status and progress', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 2,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 1,
        progress: 50,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'running'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const article = screen.getByRole('article')
      // Status label is "In Progress" when running > 0
      expect(article).toHaveAttribute(
        'aria-label',
        'Test Group: In Progress, 2 of 4 stages completed'
      )
    })

    it('has accessible progress bar with label and value text', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'in-progress',
        completed: 3,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 75,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'complete'],
        ['stage_4', 'pending'],
      ])

      render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      const progressBar = screen.getByLabelText('Test Group progress')
      expect(progressBar).toHaveAttribute('aria-valuenow', '75')
      expect(progressBar).toHaveAttribute('aria-valuetext', '75% complete')
    })

    it('hides decorative icons from screen readers', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'completed',
        completed: 4,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 100,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'complete'],
        ['stage_2', 'complete'],
        ['stage_3', 'complete'],
        ['stage_4', 'complete'],
      ])

      const { container } = render(
        <CompactGroupCard group={mockGroup} statusMeta={statusMeta} stageStatuses={stageStatuses} />
      )

      // Group icon should have aria-hidden
      const groupIcon = container.querySelector('svg[aria-hidden="true"]')
      expect(groupIcon).toBeInTheDocument()
    })
  })

  describe('custom className', () => {
    it('applies custom className to card', () => {
      const statusMeta: GroupStatusMeta = {
        status: 'pending',
        completed: 0,
        failed: 0,
        total: 4,
        skipped: 0,
        running: 0,
        progress: 0,
      }
      const stageStatuses = createMockStageStatuses([
        ['stage_1', 'pending'],
        ['stage_2', 'pending'],
        ['stage_3', 'pending'],
        ['stage_4', 'pending'],
      ])

      const { container } = render(
        <CompactGroupCard
          group={mockGroup}
          statusMeta={statusMeta}
          stageStatuses={stageStatuses}
          className="custom-test-class"
        />
      )

      const card = container.querySelector('.custom-test-class')
      expect(card).toBeInTheDocument()
    })
  })
})
