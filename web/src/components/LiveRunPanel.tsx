import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { TraceEvent } from "../types/trace";
import EventCard from "./EventCard";

interface LiveRunPanelProps {
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

export default function LiveRunPanel({
  providers,
  onStart,
  events,
  running,
  traceId,
  onOpenTrace,
}: LiveRunPanelProps) {
  const [task, setTask] = useState("Solve 23*47 and show your steps");
  const [root, setRoot] = useState(".");
  const [provider, setProvider] = useState(providers[0] ?? "heuristic");
  const [allowNet, setAllowNet] = useState(false);

  useEffect(() => {
    if (!providers.includes(provider)) {
      setProvider(providers[0] ?? "heuristic");
    }
  }, [provider, providers]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onStart({
      task,
      root,
      provider,
      allow_net: allowNet,
    });
  };

  return (
    <div className="live-run">
      <div className="live-run-form">
        <h2>Live Run</h2>
        <p>Kick off a run and watch events stream in real-time.</p>
        <form onSubmit={handleSubmit}>
          <label>
            Task
            <textarea value={task} onChange={(event) => setTask(event.target.value)} rows={3} />
          </label>
          <div className="form-row">
            <label>
              Root
              <input value={root} onChange={(event) => setRoot(event.target.value)} />
            </label>
            <label>
              Provider
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                {providers.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={allowNet}
              onChange={(event) => setAllowNet(event.target.checked)}
            />
            Allow network access
          </label>
          <button className="primary-button" type="submit" disabled={running}>
            {running ? "Running..." : "Start Run"}
          </button>
        </form>
        {traceId && !running && (
          <button className="ghost-button" type="button" onClick={() => onOpenTrace(traceId)}>
            Open Trace {traceId}
          </button>
        )}
      </div>
      <div className="live-run-stream">
        <h3>Live Timeline</h3>
        {events.length === 0 ? (
          <p className="empty">No events yet.</p>
        ) : (
          events.map((event, idx) => <EventCard key={`${event.type}-${idx}`} event={event} />)
        )}
      </div>
    </div>
  );
}
