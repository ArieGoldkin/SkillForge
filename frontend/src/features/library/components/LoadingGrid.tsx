export function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-80 bg-muted animate-pulse rounded-xl" />
      ))}
    </div>
  )
}
