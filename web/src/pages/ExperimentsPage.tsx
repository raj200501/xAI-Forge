import { useEffect, useState } from "react";
import { fetchExperimentReport, fetchExperiments } from "../lib/api";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Record<string, any>[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [report, setReport] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetchExperiments()
      .then((items) => {
        setExperiments(items);
        if (items.length > 0) {
          setSelected(items[0].experiment_id);
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchExperimentReport(selected)
      .then((payload) => setReport(payload))
      .catch(console.error);
  }, [selected]);

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Experiments</h2>
        <p>Compare A/B, shadow, canary, and fallback outcomes.</p>
      </header>
      <div className="workbench-columns">
        <div className="workbench-panel">
          <h3>Recent Experiments</h3>
          <table className="workbench-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Mode</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <tr key={exp.experiment_id} onClick={() => setSelected(exp.experiment_id)}>
                  <td>{exp.experiment_id}</td>
                  <td>{exp.summary?.mode}</td>
                  <td>{exp.summary?.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="workbench-panel">
          <h3>Comparison</h3>
          {report ? (
            <div className="comparison-panel">
              <div>
                <h4>Primary</h4>
                <p>{report.primary?.provider}</p>
                <pre className="code-block">{report.primary?.text}</pre>
              </div>
              <div>
                <h4>Secondary</h4>
                <p>{report.secondary?.provider || "-"}</p>
                <pre className="code-block">{report.secondary?.text || ""}</pre>
              </div>
              <div className="comparison-metrics">
                <span>Stability: {report.comparison?.stability_score?.toFixed(2) ?? "-"}</span>
                <span>Latency Δ: {report.comparison?.latency_delta_ms ?? "-"} ms</span>
              </div>
            </div>
          ) : (
            <p className="muted">Select an experiment to see details.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function extractExperimentIds(items: Record<string, any>[]) {
  return items.map((item) => String(item.experiment_id));
}
