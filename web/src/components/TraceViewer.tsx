import { useMemo, useState } from "react";
import type { TraceEvent, TraceManifest } from "../types/trace";
import { buildSpanTree, collectToolCalls, computeMetrics, formatTimestamp } from "../lib/trace";
import EventCard from "./EventCard";
import MetricsPanel from "./MetricsPanel";
import JsonBlock from "./JsonBlock";

interface TraceViewerProps {
  manifest?: TraceManifest | null;
  events: TraceEvent[];
  onReplay: () => void;
  replaying: boolean;
}

const tabs = ["Timeline", "Spans Tree", "Tools", "Metrics"] as const;

export default function TraceViewer({ manifest, events, onReplay, replaying }: TraceViewerProps) {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("Timeline");
  const metrics = useMemo(() => computeMetrics(events, manifest), [events, manifest]);
  const spanRows = useMemo(() => buildSpanTree(events), [events]);
  const toolCalls = useMemo(() => collectToolCalls(events), [events]);

  return (
    <div className="trace-viewer">
      <header className="trace-viewer-header">
        <div>
          <h2>Trace {manifest?.trace_id ?? ""}</h2>
          {manifest && (
            <p>
              {manifest.task} · {manifest.provider} · Started {formatTimestamp(manifest.started_at)}
            </p>
          )}
        </div>
        <div className="trace-actions">
          <button className="primary-button" type="button" onClick={onReplay} disabled={replaying}>
            {replaying ? "Replaying..." : "Replay Trace"}
          </button>
        </div>
      </header>
      <div className="tab-bar">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={activeTab === tab ? "active" : ""}
            type="button"
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {activeTab === "Timeline" && (
          <div className="timeline">
            {events.length === 0 ? (
              <p className="empty">No events available.</p>
            ) : (
              events.map((event, idx) => <EventCard key={`${event.type}-${idx}`} event={event} />)
            )}
          </div>
        )}
        {activeTab === "Spans Tree" && (
          <div className="spans-tree">
            {spanRows.length === 0 ? (
              <p className="empty">No spans recorded.</p>
            ) : (
              spanRows.map(({ event, depth }) => (
                <div key={`${event.type}-${event.span_id}`} className="span-row">
                  <div style={{ paddingLeft: `${depth * 18}px` }}>
                    <strong>{event.type}</strong>
                    <span>{event.span_id?.slice(0, 8)}</span>
                    <span>{formatTimestamp(event.ts)}</span>
                  </div>
                  <JsonBlock data={event} />
                </div>
              ))
            )}
          </div>
        )}
        {activeTab === "Tools" && (
          <div className="tools-table">
            {toolCalls.length === 0 ? (
              <p className="empty">No tool calls recorded.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th>Args</th>
                    <th>Result</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {toolCalls.map((call) => (
                    <tr key={call.id}>
                      <td>{call.name}</td>
                      <td>
                        <JsonBlock data={call.arguments} />
                      </td>
                      <td>
                        {call.error ? (
                          <span className="error">{call.error}</span>
                        ) : (
                          <JsonBlock data={call.result} />
                        )}
                      </td>
                      <td>{call.error ? "error" : "ok"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        {activeTab === "Metrics" && <MetricsPanel metrics={metrics} />}
      </div>
    </div>
  );
}
