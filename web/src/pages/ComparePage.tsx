import type { TraceEvent, TraceManifest } from "../types/trace";
import ComparePanel from "../components/ComparePanel";

interface ComparePageProps {
  traces: TraceManifest[];
  leftId: string;
  rightId: string;
  onSelectLeft: (value: string) => void;
  onSelectRight: (value: string) => void;
  leftEvents: TraceEvent[];
  rightEvents: TraceEvent[];
}

export default function ComparePage({
  traces,
  leftId,
  rightId,
  onSelectLeft,
  onSelectRight,
  leftEvents,
  rightEvents,
}: ComparePageProps) {
  return (
    <ComparePanel
      traces={traces}
      leftId={leftId}
      rightId={rightId}
      onSelectLeft={onSelectLeft}
      onSelectRight={onSelectRight}
      leftEvents={leftEvents}
      rightEvents={rightEvents}
    />
  );
}
