interface AnalysisHeaderProps {
  title: string | null;
  url: string;
}

export function AnalysisHeader({ title, url }: AnalysisHeaderProps) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold mb-2">{title || "Analysis"}</h1>
      <p className="text-muted-foreground">{url}</p>
    </div>
  );
}
