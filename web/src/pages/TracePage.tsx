import type { TraceEvent, TraceManifest } from "../types/trace";
import TraceViewer from "../components/TraceViewer";

interface TracePageProps {
  manifest?: TraceManifest | null;
  events: TraceEvent[];
  onReplay: () => void;
  replaying: boolean;
}

export default function TracePage({ manifest, events, onReplay, replaying }: TracePageProps) {
  if (!manifest) {
    return <div className="empty">Select a trace to view its timeline.</div>;
  }
  return <TraceViewer manifest={manifest} events={events} onReplay={onReplay} replaying={replaying} />;
}
