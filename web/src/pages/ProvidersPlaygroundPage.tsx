import { useEffect, useState } from "react";
import { fetchProviders, runGateway } from "../lib/api";

export default function ProvidersPlaygroundPage() {
  const [providers, setProviders] = useState<string[]>([]);
  const [provider, setProvider] = useState("mock");
  const [prompt, setPrompt] = useState("Summarize the latest run.");
  const [output, setOutput] = useState<Record<string, any> | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetchProviders().then(setProviders).catch(console.error);
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      const result = await runGateway({
        provider,
        messages: [{ role: "user", content: prompt }],
      });
      setOutput(result);
    } catch (error) {
      console.error(error);
      setOutput({ error: String(error) });
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="workbench-page">
      <header className="workbench-header">
        <h2>Provider Playground</h2>
        <p>Send a single prompt through the gateway with request metadata.</p>
      </header>
      <div className="workbench-panel">
        <div className="form-grid">
          <label>
            Provider
            <select value={provider} onChange={(event) => setProvider(event.target.value)}>
              {["mock", ...providers].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            Prompt
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          </label>
        </div>
        <button type="button" className="primary-button" onClick={handleRun} disabled={running}>
          {running ? "Running..." : "Run"}
        </button>
        <div className="workbench-output">
          <h3>Output</h3>
          <pre className="code-block">{output ? JSON.stringify(output, null, 2) : ""}</pre>
        </div>
      </div>
    </section>
  );
}

export function buildGatewayPayload(provider: string, prompt: string) {
  return { provider, messages: [{ role: "user", content: prompt }] };
}
