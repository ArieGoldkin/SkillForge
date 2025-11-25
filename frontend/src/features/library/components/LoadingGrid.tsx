const SKELETON_KEYS = ['skeleton-1', 'skeleton-2', 'skeleton-3', 'skeleton-4'] as const

export function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {SKELETON_KEYS.map((key) => (
        <div key={key} className="h-80 bg-muted animate-pulse rounded-xl" />
      ))}
    </div>
  )
}
