# xAI-Forge

xAI-Forge is a deterministic agent runtime with a built-in trace viewer and an OSS-friendly
workflow. It is designed for reproducible evaluation, streaming runs, and end-to-end
observability.

## What you get

- Deterministic runs with event hashing
- A local-first trace store (`.xaiforge/traces`)
- A web UI for browsing traces and timelines
- A typed Python SDK for automation and integrations
- Exporters for Markdown, HTML, and JSON reports
- A plugin system for metrics and redaction

## Quickstart

```bash
python -m xaiforge run --task "Summarize the repo"
python -m xaiforge serve
cd web && npm install && npm run dev
```

## Docs map

- Architecture: see `ARCHITECTURE.md`
- Event schema: `docs/EVENT_SPEC.md`
- Security model: `docs/SECURITY.md`
- Tooling + providers: `docs/TOOLS.md`, `docs/PROVIDERS.md`
