import { useMemo } from "react";
import type { TraceEvent, TraceManifest } from "../types/trace";
import { computeMetrics, formatDuration } from "../lib/trace";

interface ComparePanelProps {
  traces: TraceManifest[];
  leftId: string;
  rightId: string;
  onSelectLeft: (value: string) => void;
  onSelectRight: (value: string) => void;
  leftEvents: TraceEvent[];
  rightEvents: TraceEvent[];
}

export default function ComparePanel({
  traces,
  leftId,
  rightId,
  onSelectLeft,
  onSelectRight,
  leftEvents,
  rightEvents,
}: ComparePanelProps) {
  const leftManifest = traces.find((trace) => trace.trace_id === leftId);
  const rightManifest = traces.find((trace) => trace.trace_id === rightId);
  const leftMetrics = useMemo(() => computeMetrics(leftEvents, leftManifest), [leftEvents, leftManifest]);
  const rightMetrics = useMemo(
    () => computeMetrics(rightEvents, rightManifest),
    [rightEvents, rightManifest],
  );

  const toolDiffs = useMemo(() => {
    const tally = (events: TraceEvent[]) => {
      const counts: Record<string, number> = {};
      for (const event of events) {
        if (event.type === "tool_call") {
          const name = String(event.tool_name ?? "unknown");
          counts[name] = (counts[name] || 0) + 1;
        }
      }
      return counts;
    };
    const left = tally(leftEvents);
    const right = tally(rightEvents);
    const tools = new Set([...Object.keys(left), ...Object.keys(right)]);
    return Array.from(tools).map((tool) => ({
      tool,
      left: left[tool] || 0,
      right: right[tool] || 0,
    }));
  }, [leftEvents, rightEvents]);

  return (
    <div className="compare-panel">
      <header>
        <h2>Compare Runs</h2>
        <p>Compare the telemetry of two traces side-by-side.</p>
      </header>
      <div className="compare-selectors">
        <label>
          Trace A
          <select value={leftId} onChange={(event) => onSelectLeft(event.target.value)}>
            <option value="">Select trace</option>
            {traces.map((trace) => (
              <option key={trace.trace_id} value={trace.trace_id}>
                {trace.trace_id}
              </option>
            ))}
          </select>
        </label>
        <label>
          Trace B
          <select value={rightId} onChange={(event) => onSelectRight(event.target.value)}>
            <option value="">Select trace</option>
            {traces.map((trace) => (
              <option key={trace.trace_id} value={trace.trace_id}>
                {trace.trace_id}
              </option>
            ))}
          </select>
        </label>
      </div>
      {leftEvents.length === 0 || rightEvents.length === 0 ? (
        <p className="empty">Select two traces to see a comparison.</p>
      ) : (
        <div className="compare-grid">
          <div className="compare-card">
            <h3>Metrics</h3>
            <table>
              <tbody>
                <tr>
                  <th>Duration</th>
                  <td>{formatDuration(leftMetrics.duration_s)}</td>
                  <td>{formatDuration(rightMetrics.duration_s)}</td>
                </tr>
                <tr>
                  <th>Events</th>
                  <td>{leftMetrics.event_count}</td>
                  <td>{rightMetrics.event_count}</td>
                </tr>
                <tr>
                  <th>Tool Calls</th>
                  <td>{leftMetrics.tool_call_count}</td>
                  <td>{rightMetrics.tool_call_count}</td>
                </tr>
                <tr>
                  <th>Errors</th>
                  <td>{leftMetrics.error_count}</td>
                  <td>{rightMetrics.error_count}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="compare-card">
            <h3>Tool Frequency</h3>
            <table>
              <thead>
                <tr>
                  <th>Tool</th>
                  <th>Trace A</th>
                  <th>Trace B</th>
                </tr>
              </thead>
              <tbody>
                {toolDiffs.map((item) => (
                  <tr key={item.tool}>
                    <td>{item.tool}</td>
                    <td>{item.left}</td>
                    <td>{item.right}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
