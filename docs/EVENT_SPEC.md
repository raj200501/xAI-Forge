# Event Specification

All events share a common base payload:

```json
{
  "trace_id": "202409141200000000",
  "ts": "2024-09-14T12:00:00.000Z",
  "type": "run_start",
  "span_id": "<uuid>",
  "parent_span_id": null
}
```

## Event Types

### `run_start`
Required fields:

- `trace_id`
- `ts`
- `type`: `run_start`
- `span_id`
- `task`
- `provider`
- `root_dir`

Example:
```json
{
  "trace_id": "202409141200000000",
  "ts": "2024-09-14T12:00:00.000Z",
  "type": "run_start",
  "span_id": "a1b2c3",
  "task": "Solve 23*47",
  "provider": "heuristic",
  "root_dir": "."
}
```

### `plan`
Required fields:

- `trace_id`
- `ts`
- `type`: `plan`
- `span_id`
- `steps` (array of strings)

### `message`
Required fields:

- `trace_id`
- `ts`
- `type`: `message`
- `span_id`
- `role` (`system`, `assistant`, `tool`)
- `content`

### `tool_call`
Required fields:

- `trace_id`
- `ts`
- `type`: `tool_call`
- `span_id`
- `tool_name`
- `arguments`

### `tool_result`
Required fields:

- `trace_id`
- `ts`
- `type`: `tool_result`
- `span_id`
- `tool_name`
- `result`

### `tool_error`
Required fields:

- `trace_id`
- `ts`
- `type`: `tool_error`
- `span_id`
- `tool_name`
- `error`

### `run_end`
Required fields:

- `trace_id`
- `ts`
- `type`: `run_end`
- `span_id`
- `status` (`ok` or `error`)
- `summary`
- `final_hash`
- `event_count`

Example:
```json
{
  "trace_id": "202409141200000000",
  "ts": "2024-09-14T12:00:10.000Z",
  "type": "run_end",
  "span_id": "d4e5f6",
  "status": "ok",
  "summary": "Answer: 1081",
  "final_hash": "<sha256>",
  "event_count": 42
}
```

## Span Relationships

- `span_id` is a unique identifier for the event.
- `parent_span_id` links nested events together (e.g., tool calls inside a run).
- The UI uses `span_id`/`parent_span_id` to render the tree view.
