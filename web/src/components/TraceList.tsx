import type { TraceManifest } from "../types/trace";
import { formatDuration, formatTimestamp } from "../lib/trace";

interface TraceListProps {
  traces: TraceManifest[];
  activeId?: string | null;
  onSelect: (traceId: string) => void;
}

export default function TraceList({ traces, activeId, onSelect }: TraceListProps) {
  return (
    <div className="trace-list">
      {traces.length === 0 && <p className="empty">No traces yet. Run a task to get started.</p>}
      {traces.map((trace) => (
        <button
          key={trace.trace_id}
          className={`trace-card ${activeId === trace.trace_id ? "active" : ""}`}
          type="button"
          onClick={() => onSelect(trace.trace_id)}
        >
          <div className="trace-card-header">
            <span className="trace-id">{trace.trace_id}</span>
            <span className="trace-provider">{trace.provider}</span>
          </div>
          <p>{trace.task}</p>
          <div className="trace-card-meta">
            <span>{formatTimestamp(trace.started_at)}</span>
            <span>{formatDuration(trace.duration_s)}</span>
          </div>
          <div className="trace-card-stats">
            <span>{trace.event_count ?? 0} events</span>
            <span>{trace.tool_call_count ?? 0} tools</span>
          </div>
        </button>
      ))}
    </div>
  );
}
