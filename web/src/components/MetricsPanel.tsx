import type { MetricsSummary } from "../types/trace";
import { formatDuration } from "../lib/trace";

interface MetricsPanelProps {
  metrics: MetricsSummary;
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <div className="metrics-grid">
      <div className="metric-card">
        <p>Duration</p>
        <strong>{formatDuration(metrics.duration_s)}</strong>
      </div>
      <div className="metric-card">
        <p>Events</p>
        <strong>{metrics.event_count}</strong>
      </div>
      <div className="metric-card">
        <p>Events / sec</p>
        <strong>{metrics.events_per_sec ? metrics.events_per_sec.toFixed(2) : "–"}</strong>
      </div>
      <div className="metric-card">
        <p>Tool Calls</p>
        <strong>{metrics.tool_call_count}</strong>
      </div>
      <div className="metric-card">
        <p>Errors</p>
        <strong>{metrics.error_count}</strong>
      </div>
      <div className="metric-card">
        <p>Top Tools</p>
        {metrics.top_tools.length ? (
          <ul>
            {metrics.top_tools.map((tool) => (
              <li key={tool.name}>
                {tool.name} <span>{tool.count}</span>
              </li>
            ))}
          </ul>
        ) : (
          <span>–</span>
        )}
      </div>
    </div>
  );
}
