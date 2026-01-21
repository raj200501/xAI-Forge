# Architecture

xAI-Forge provides a deterministic execution runtime backed by a trace store and a UI
for inspection, replay, and export.

```mermaid
graph TD
  CLI[CLI + SDK] --> API[FastAPI server]
  API --> Runner[Agent runner]
  Runner --> Providers[Provider implementations]
  Runner --> Tools[Tool registry]
  Runner --> TraceStore[Trace store (.xaiforge/traces)]
  TraceStore --> UI[Web UI]
  TraceStore --> Exporters[Exporters]
  TraceStore --> Plugins[Plugins]
```

## Data flow

1. A run is started from the CLI, SDK, or API.
2. The runner emits a stream of typed events (`run_start`, `tool_call`, `run_end`, ...).
3. Events are hashed and persisted in `.xaiforge/traces` with a manifest for integrity.
4. The UI pulls trace manifests and event payloads from the API.
5. Exporters generate Markdown/HTML/JSON reports for sharing.
6. Plugins can redact sensitive fields or aggregate metrics in parallel with the run.

## Components

- **Agent runner**: `xaiforge/agent/runner.py`
- **Event schema**: `xaiforge/events.py`
- **Trace store**: `xaiforge/trace_store.py`
- **Plugins**: `xaiforge/plugins/*`
- **Exporters**: `xaiforge/exporters.py`
- **Query DSL**: `xaiforge/query.py`
- **SDK**: `xaiforge_sdk/*`

## Observability and policy

- **Observability**: `xaiforge/observability/*` provides structured logging, in-process
  metrics, and optional OpenTelemetry scaffolding (disabled by default).
- **Policy engine**: `xaiforge/policy/*` evaluates tool calls against allow/deny rules
  and writes policy reports to `.xaiforge/policy/` when enabled.
- **Bench reports**: `xaiforge/benchmarks/report.py` writes a quick run summary to
  `.xaiforge/bench/latest.md`.
