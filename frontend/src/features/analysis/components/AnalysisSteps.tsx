interface MockTimestamps {
  twoMinAgo: string;
  ninetySecAgo: string;
  oneMinAgo: string;
  fortyFiveSecAgo: string;
  now: string;
}

interface AnalysisStepsProps {
  isComplete: boolean;
  mockTimestamps: MockTimestamps;
}

type StepStatus = "completed" | "in-progress" | "pending";

export function AnalysisSteps({ isComplete, mockTimestamps }: AnalysisStepsProps) {
  return [
    {
      id: "1",
      title: "Content Extraction",
      status: "completed" as StepStatus,
      description: "Successfully extracted 1,250 words",
      timestamp: new Date(mockTimestamps.twoMinAgo),
    },
    {
      id: "2",
      title: "Embedding Generation",
      status: "completed" as StepStatus,
      description: "Generated 768-dimensional embeddings",
      timestamp: new Date(mockTimestamps.ninetySecAgo),
    },
    {
      id: "3",
      title: "Agent Analysis",
      status: (isComplete ? "completed" : "in-progress") as StepStatus,
      description: isComplete
        ? "Analysis complete"
        : "Analyzing code patterns...",
      timestamp: new Date(mockTimestamps.oneMinAgo),
    },
    {
      id: "4",
      title: "Report Generation",
      status: (isComplete ? "completed" : "pending") as StepStatus,
      description: isComplete
        ? "Implementation guide ready"
        : "Waiting for analysis...",
      timestamp: isComplete ? new Date(mockTimestamps.now) : undefined,
    },
  ];
}
