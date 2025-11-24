export function NotFoundState() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4">Analysis Not Found</h1>
      <p className="text-muted-foreground">
        The requested analysis could not be found.
      </p>
    </div>
  );
}
