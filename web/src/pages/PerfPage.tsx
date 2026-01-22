import { useEffect, useMemo, useState } from "react";
import { fetchReport, fetchReportList } from "../lib/api";

function Sparkline({ values }: { values: number[] }) {
  if (!values.length) return <span className="muted">-</span>;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - ((value - min) / Math.max(max - min, 1)) * 100;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" className="sparkline">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" />
    </svg>
  );
}

export default function PerfPage() {
  const [reports, setReports] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [reportPayload, setReportPayload] = useState<any>(null);

  useEffect(() => {
    fetchReportList("perf")
      .then((items) => {
        setReports(items);
        setSelected(items[0] || null);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchReport("perf", selected)
      .then((payload) => setReportPayload(payload))
      .catch(console.error);
  }, [selected]);

  const latencySeries = useMemo(() => {
    if (!reportPayload) return [];
    return reportPayload.metrics?.latencies_ms || [];
  }, [reportPayload]);

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Performance Lab</h2>
        <p>Benchmarks, load tests, and regression baselines.</p>
      </header>
      <div className="workbench-columns">
        <div className="workbench-panel">
          <h3>Reports</h3>
          <table className="workbench-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Suite</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((name) => (
                <tr key={name} onClick={() => setSelected(name)}>
                  <td>{name}</td>
                  <td>{reportPayload?.suite || reportPayload?.duration_s || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="workbench-panel">
          <h3>Latency Distribution</h3>
          <Sparkline values={latencySeries.slice(0, 40)} />
          <pre className="code-block">{reportPayload ? JSON.stringify(reportPayload.summary, null, 2) : ""}</pre>
        </div>
      </div>
    </section>
  );
}

export function buildLatencySeries(payload: any): number[] {
  if (!payload) return [];
  return payload.metrics?.latencies_ms || [];
}
