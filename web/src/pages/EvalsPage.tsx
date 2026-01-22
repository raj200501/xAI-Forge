import { useEffect, useState } from "react";
import { fetchReport, fetchReportList } from "../lib/api";

export default function EvalsPage() {
  const [reports, setReports] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [reportPayload, setReportPayload] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchReportList("evals")
      .then((items) => {
        setReports(items);
        setSelected(items[0] || null);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchReport("evals", selected)
      .then((payload) => setReportPayload(payload))
      .catch(console.error);
  }, [selected]);

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Eval Suites</h2>
        <p>Regression tracking and scorecards for eval datasets.</p>
      </header>
      <div className="workbench-columns">
        <div className="workbench-panel">
          <h3>Available Reports</h3>
          <ul className="signal-list">
            {reports.map((name) => (
              <li key={name}>
                <button
                  type="button"
                  className={selected === name ? "active" : ""}
                  onClick={() => setSelected(name)}
                >
                  {name}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="workbench-panel">
          <h3>Report Detail</h3>
          {reportPayload ? (
            <pre className="code-block">{JSON.stringify(reportPayload, null, 2)}</pre>
          ) : (
            <p className="muted">Select an eval report to inspect.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function pickDefaultReport(reports: string[]) {
  return reports[0] || null;
}
