import { useQuery } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";

import { mockAnalyzeAPI } from "@/services/mock.service";

import { ActivityColumn } from "./components/ActivityColumn";
import { AnalysisHeader } from "./components/AnalysisHeader";
import { LoadingState } from "./components/LoadingState";
import { NotFoundState } from "./components/NotFoundState";
import { ProgressColumn } from "./components/ProgressColumn";
import { useMockTimestamps } from "./hooks/useMockTimestamps";

export default function AnalyzeResult() {
  const { id } = useParams({ from: "/analyze/$id" });

  const { data: analysis, isLoading } = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => mockAnalyzeAPI.getAnalysis(id),
  });

  const mockTimestamps = useMockTimestamps();

  if (isLoading) return <LoadingState />;
  if (!analysis) return <NotFoundState />;

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader title={analysis.title} url={analysis.url} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ProgressColumn status={analysis.status} mockTimestamps={mockTimestamps} />
        <ActivityColumn mockTimestamps={mockTimestamps} />
      </div>
    </div>
  );
}
