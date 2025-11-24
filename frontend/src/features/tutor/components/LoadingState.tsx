export function LoadingState() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-muted rounded w-1/4" />
        <div className="h-96 bg-muted rounded" />
      </div>
    </div>
  );
}
