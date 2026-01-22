import { useEffect, useState } from "react";
import { fetchPlugins, fetchPolicySummary } from "../lib/api";

export default function PoliciesPage() {
  const [plugins, setPlugins] = useState<string[]>([]);
  const [policySummary, setPolicySummary] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetchPlugins().then(setPlugins).catch(console.error);
    fetchPolicySummary().then(setPolicySummary).catch(console.error);
  }, []);

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Policies & Plugins</h2>
        <p>Enable policy controls and custom extensions for internal tooling.</p>
      </header>
      <div className="workbench-columns">
        <div className="workbench-panel">
          <h3>Available Plugins</h3>
          <ul className="signal-list">
            {plugins.map((plugin) => (
              <li key={plugin}>{plugin}</li>
            ))}
          </ul>
          <p className="muted">Enable plugins via CLI: <code>--plugins name1,name2</code></p>
        </div>
        <div className="workbench-panel">
          <h3>Policy Summary</h3>
          {policySummary?.enabled ? (
            <pre className="code-block">{JSON.stringify(policySummary.summary, null, 2)}</pre>
          ) : (
            <p className="muted">No policy configured via environment.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function formatPluginCount(plugins: string[]) {
  return `${plugins.length} plugins`;
}
