import { useEffect, useMemo, useState } from "react";
import { fetchExperiments, fetchManifests, fetchReportList } from "../lib/api";
import type { TraceManifest } from "../types/trace";

export default function DashboardPage() {
  const [manifests, setManifests] = useState<TraceManifest[]>([]);
  const [experiments, setExperiments] = useState<Record<string, unknown>[]>([]);
  const [perfReports, setPerfReports] = useState<string[]>([]);

  useEffect(() => {
    fetchManifests().then(setManifests).catch(console.error);
    fetchExperiments().then(setExperiments).catch(console.error);
    fetchReportList("perf").then(setPerfReports).catch(console.error);
  }, []);

  const summary = useMemo(() => {
    const totalTraces = manifests.length;
    const errorRate = totalTraces
      ? manifests.filter((item) => Number(item.error_count || 0) > 0).length / totalTraces
      : 0;
    const avgToolCalls = totalTraces
      ? manifests.reduce((sum, item) => sum + Number(item.tool_call_count || 0), 0) / totalTraces
      : 0;
    const providers = Array.from(new Set(manifests.map((item) => item.provider).filter(Boolean)));
    return { totalTraces, errorRate, avgToolCalls, providers };
  }, [manifests]);

  const recentRuns = manifests.slice(0, 6);

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Workbench Dashboard</h2>
        <p>Operational pulse for traces, experiments, and perf runs.</p>
      </header>
      <div className="card-grid">
        <div className="workbench-card">
          <span>Total traces</span>
          <strong>{summary.totalTraces}</strong>
        </div>
        <div className="workbench-card">
          <span>Error rate</span>
          <strong>{(summary.errorRate * 100).toFixed(1)}%</strong>
        </div>
        <div className="workbench-card">
          <span>Avg tool calls</span>
          <strong>{summary.avgToolCalls.toFixed(1)}</strong>
        </div>
        <div className="workbench-card">
          <span>Recent providers</span>
          <strong>{summary.providers.slice(0, 3).join(", ") || "-"}</strong>
        </div>
      </div>
      <div className="workbench-columns">
        <div className="workbench-panel">
          <h3>Recent Runs</h3>
          <table className="workbench-table">
            <thead>
              <tr>
                <th>Trace</th>
                <th>Provider</th>
                <th>Duration</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={run.trace_id}>
                  <td>{run.trace_id}</td>
                  <td>{run.provider}</td>
                  <td>{Number(run.duration_s || 0).toFixed(2)}s</td>
                  <td>{run.error_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="workbench-panel">
          <h3>Signals</h3>
          <ul className="signal-list">
            <li>{experiments.length} experiments tracked</li>
            <li>{perfReports.length} perf reports available</li>
            <li>{summary.providers.length} active providers</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

export function summarizeDashboard(manifests: TraceManifest[]) {
  const totalTraces = manifests.length;
  const errorRate = totalTraces
    ? manifests.filter((item) => Number(item.error_count || 0) > 0).length / totalTraces
    : 0;
  const avgToolCalls = totalTraces
    ? manifests.reduce((sum, item) => sum + Number(item.tool_call_count || 0), 0) / totalTraces
    : 0;
  const providers = Array.from(new Set(manifests.map((item) => item.provider).filter(Boolean)));
  return { totalTraces, errorRate, avgToolCalls, providers };
}
