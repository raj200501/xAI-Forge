import { useState } from "react";
import type { TraceEvent } from "../types/trace";
import JsonBlock from "./JsonBlock";
import { formatTimestamp } from "../lib/trace";

interface EventCardProps {
  event: TraceEvent;
}

export default function EventCard({ event }: EventCardProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="event-card">
      <header>
        <div>
          <strong>{event.type}</strong>
          <span>{formatTimestamp(event.ts)}</span>
        </div>
        <button className="ghost-button" type="button" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Hide" : "Details"}
        </button>
      </header>
      <div className="event-meta">
        {event.span_id && <span>Span: {event.span_id.slice(0, 8)}</span>}
        {event.parent_span_id && <span>Parent: {String(event.parent_span_id).slice(0, 8)}</span>}
      </div>
      {expanded && <JsonBlock data={event} />}
    </div>
  );
}
