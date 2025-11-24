import { AgentActivityFeed } from "@/shared/components/features/analysis/AgentActivityFeed";

interface MockTimestamps {
  twoMinAgo: string;
  ninetySecAgo: string;
  oneMinAgo: string;
  fortyFiveSecAgo: string;
  now: string;
}

interface ActivityColumnProps {
  mockTimestamps: MockTimestamps;
}

export function ActivityColumn({ mockTimestamps }: ActivityColumnProps) {
  return (
    <div className="lg:col-span-1">
      <AgentActivityFeed
        activities={[
          {
            id: "1",
            agentName: "Content Extractor",
            action: "Extracted article content",
            timestamp: new Date(mockTimestamps.twoMinAgo),
          },
          {
            id: "2",
            agentName: "Embedding Service",
            action: "Generated content embeddings",
            timestamp: new Date(mockTimestamps.ninetySecAgo),
          },
          {
            id: "3",
            agentName: "Code Analyzer",
            action: "Identified 12 code examples",
            timestamp: new Date(mockTimestamps.oneMinAgo),
          },
          {
            id: "4",
            agentName: "Pattern Detector",
            action: "Found 8 implementation patterns",
            timestamp: new Date(mockTimestamps.fortyFiveSecAgo),
          },
        ]}
      />
    </div>
  );
}
