import type { TraceEvent } from "../types/trace";
import LiveRunPanel from "../components/LiveRunPanel";

interface LiveRunPageProps {
  providers: string[];
  onStart: (payload: {
    task: string;
    root: string;
    provider: string;
    allow_net: boolean;
  }) => Promise<void>;
  events: TraceEvent[];
  running: boolean;
  traceId?: string | null;
  onOpenTrace: (traceId: string) => void;
}

export default function LiveRunPage({
  providers,
  onStart,
  events,
  running,
  traceId,
  onOpenTrace,
}: LiveRunPageProps) {
  return (
    <LiveRunPanel
      providers={providers}
      onStart={onStart}
      events={events}
      running={running}
      traceId={traceId}
      onOpenTrace={onOpenTrace}
    />
  );
}
