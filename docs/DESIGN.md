# xAI-Forge Runtime Design

xAI-Forge is a deterministic agent runtime that emits an immutable event stream for
every run. The runtime is intentionally small, offline-friendly, and built around
traceability.

## Event Model

Every run writes a JSONL stream of events to `.xaiforge/traces/<trace_id>.jsonl`.
The event stream is append-only and includes:

- `run_start` – canonical metadata for the run (task, provider, root).
- `plan` – optional high-level plan steps.
- `message` – model responses or tool outputs.
- `tool_call` / `tool_result` / `tool_error` – tool invocation lifecycle.
- `run_end` – status, summary, integrity hash, event count.

The web UI and CLI treat the stream as the source of truth. Manifests and reports
are derived artifacts stored alongside the trace.

## Determinism and Replay

Determinism is enforced through:

1. **Fixed tool registry** – tools are pure functions scoped to the run's root.
2. **Stable trace IDs** – generated on start, used across the stream.
3. **Event hashing** – every non-`run_end` event line updates a rolling SHA-256
   hash so replays can validate integrity.

The replay command reads the event log, recomputes the hash, and emits a final
`run_end` event with `integrity_ok` indicating whether the replay matched the
recorded hash.

## Hashing & Integrity

`RollingHasher` updates with each event line (excluding `run_end`) by hashing the
line plus newline delimiter. The final digest is written to:

- `manifest.final_hash`
- `run_end.final_hash`
- `.report.md` summary

Integrity checks are purely local and offline-friendly.

## Storage Layout

```
.xaiforge/
  traces/
    <trace_id>.jsonl
    <trace_id>.manifest.json
    <trace_id>.report.md
  bench/
    latest.md
```

## UI Data Flow

The Flight Recorder UI consumes:

- `/api/traces` for trace manifests + derived metrics
- `/api/traces/<id>/events` for full event streams
- `/api/run` and `/api/replay/<id>` for SSE streaming

All rendering is driven by the raw events to keep replay fidelity intact.
