# Features

## Trace exporters

Use the CLI to export traces in Markdown, HTML, or JSON.

```bash
python -m xaiforge export <trace_id> --format markdown
python -m xaiforge export <trace_id> --format html
python -m xaiforge export <trace_id> --format json
```

The Markdown report includes summary, metrics, tool calls, errors, and timeline sections.
The HTML report is self-contained with embedded JSON.

## Plugins

Plugins can observe runs and mutate events before they are persisted.

Available plugins:

- `metrics_collector`: collects counts and writes `*.metrics.json` per trace
- `redactor`: redacts emails and token-like secrets in trace output

Enable plugins via CLI:

```bash
python -m xaiforge run --task "Summarize" --plugins metrics_collector,redactor
```

## Trace query language

Search across all events with a small DSL:

```bash
python -m xaiforge query "type=tool_error AND tool=http_get"
python -m xaiforge query "task~\"Summarize\""
```

Operators:

- `=` exact match
- `~` substring match
- `AND` to combine conditions

## Bench reports

Every run writes a bench report under `.xaiforge/bench/` with a human-friendly summary
of the plan, tool usage, and timing. The latest run is mirrored to `bench/latest.md`
for quick review.

## Policy guardrails

Policy files define allow/deny/monitor rules for tool calls. Policies are optional and
enabled by setting `XAIFORGE_POLICY_FILE` to a JSON policy file.

```bash
XAIFORGE_POLICY_FILE=examples/policy-demo.json python -m xaiforge run --task "Solve 2+2"
```

## Observability pack

Optional structured logging and in-process metrics can be enabled via environment variables:

```bash
XAIFORGE_ENABLE_LOGGING=1 XAIFORGE_LOG_FORMAT=json \
XAIFORGE_ENABLE_METRICS=1 python -m xaiforge run --task "Solve 2+2"
```
