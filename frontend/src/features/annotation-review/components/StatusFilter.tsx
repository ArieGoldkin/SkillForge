/**
 * Status filter tabs for annotation queue.
 */

import { Tabs, TabsList, TabsTrigger } from '@shared/components/ui/tabs'

interface StatusFilterProps {
  value: 'all' | 'pending' | 'reviewed'
  onChange: (value: 'all' | 'pending' | 'reviewed') => void
  total: number
}

export function StatusFilter({ value, onChange, total }: StatusFilterProps) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Status:</span>
        <Tabs value={value} onValueChange={(v) => onChange(v as 'all' | 'pending' | 'reviewed')}>
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
  )
}
