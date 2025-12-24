import { useEffect, useState } from "react";
import { fetchManifests, fetchTraceEvents, replayTrace } from "./lib/api";

interface Manifest {
  trace_id: string;
  task: string;
  provider: string;
  started_at: string;
  ended_at?: string;
  event_count?: number;
}

interface EventPayload {
  type: string;
  ts: string;
  span_id?: string;
  parent_span_id?: string;
  [key: string]: unknown;
}

export default function App() {
  const [manifests, setManifests] = useState<Manifest[]>([]);
  const [active, setActive] = useState<Manifest | null>(null);
  const [events, setEvents] = useState<EventPayload[]>([]);
  const [replaying, setReplaying] = useState(false);

  useEffect(() => {
    fetchManifests().then(setManifests).catch(console.error);
  }, []);

  const loadTrace = async (manifest: Manifest) => {
    setActive(manifest);
    const data = await fetchTraceEvents(manifest.trace_id);
    setEvents(data);
  };

  const handleReplay = async () => {
    if (!active) return;
    setReplaying(true);
    const stream = await replayTrace(active.trace_id);
    setEvents(stream);
    setReplaying(false);
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>xAI-Forge</h2>
        <p>Traces</p>
        {manifests.map((manifest) => (
          <div className="card" key={manifest.trace_id}>
            <strong>{manifest.trace_id}</strong>
            <p>{manifest.task}</p>
            <small>{manifest.provider}</small>
            <div>
              <button onClick={() => loadTrace(manifest)}>View</button>
            </div>
          </div>
        ))}
      </aside>
      <main className="main">
        {active ? (
          <>
            <h2>Trace {active.trace_id}</h2>
            <button onClick={handleReplay} disabled={replaying}>
              {replaying ? "Replaying..." : "Replay"}
            </button>
            <div>
              {events.map((event, idx) => (
                <div className="card" key={`${event.type}-${idx}`}>
                  <strong>{event.type}</strong>
                  <p>{event.ts}</p>
                  <pre>{JSON.stringify(event, null, 2)}</pre>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="card">Select a trace to view events.</div>
        )}
      </main>
    </div>
  );
}
