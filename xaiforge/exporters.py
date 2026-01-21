from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xaiforge.trace_store import TraceReader, list_manifests


def export_trace(
    trace_id: str,
    export_format: str,
    output_path: Path | None = None,
    base_dir: Path | None = None,
) -> Path:
    base_dir = base_dir or Path(".xaiforge")
    reader = TraceReader(base_dir, trace_id)
    manifest = reader.load_manifest()
    events = [json.loads(line) for line in reader.iter_events() if line.strip()]

    export_dir = base_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if export_format == "json":
        payload = {"manifest": manifest, "events": events}
        output_path = output_path or export_dir / f"{trace_id}.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path
    if export_format == "markdown":
        output_path = output_path or export_dir / f"{trace_id}.md"
        output_path.write_text(_render_markdown(manifest, events), encoding="utf-8")
        return output_path
    if export_format == "html":
        output_path = output_path or export_dir / f"{trace_id}.html"
        output_path.write_text(_render_html(manifest, events), encoding="utf-8")
        return output_path
    raise ValueError(f"Unsupported export format: {export_format}")


def export_latest(export_format: str, base_dir: Path | None = None) -> Path:
    base_dir = base_dir or Path(".xaiforge")
    manifests = list_manifests(base_dir)
    if not manifests:
        raise FileNotFoundError("No traces found")
    trace_id = manifests[0]["trace_id"]
    return export_trace(trace_id, export_format, base_dir=base_dir)


def _render_markdown(manifest: dict[str, Any], events: list[dict[str, Any]]) -> str:
    metrics = _summarize(events, manifest)
    tool_calls = _tool_calls(events)
    errors = _errors(events)
    timeline = _timeline(events)
    lines = [
        f"# Trace {manifest.get('trace_id')}",
        "",
        "## Summary",
        f"- Task: {manifest.get('task')}",
        f"- Provider: {manifest.get('provider')}",
        f"- Status: {metrics.get('status')}",
        f"- Events: {metrics.get('event_count')}",
        f"- Tool calls: {metrics.get('tool_call_count')}",
        f"- Errors: {metrics.get('error_count')}",
        f"- Duration: {metrics.get('duration_s')}s",
        "",
        "## Metrics",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Event count | {metrics.get('event_count')} |",
        f"| Tool calls | {metrics.get('tool_call_count')} |",
        f"| Errors | {metrics.get('error_count')} |",
        f"| Duration (s) | {metrics.get('duration_s')} |",
        "",
        "## Tool calls",
    ]
    if tool_calls:
        lines.append("| Tool | Arguments |")
        lines.append("| --- | --- |")
        for call in tool_calls:
            lines.append(f"| {call['tool_name']} | `{json.dumps(call['arguments'])}` |")
    else:
        lines.append("No tool calls recorded.")
    lines.extend(["", "## Errors"])
    if errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("No errors recorded.")
    lines.extend(["", "## Timeline", "| Timestamp | Type | Detail |", "| --- | --- | --- |"])
    for item in timeline:
        lines.append(f"| {item['ts']} | {item['type']} | {item['detail']} |")
    return "\n".join(lines) + "\n"


def _render_html(manifest: dict[str, Any], events: list[dict[str, Any]]) -> str:
    payload = json.dumps({"manifest": manifest, "events": events}, indent=2)
    metrics = _summarize(events, manifest)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>xAI-Forge Trace {manifest.get("trace_id")}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; background: #0b0f19; color: #e5e7eb; }}
    .card {{ background: #111827; padding: 24px; border-radius: 12px; margin-bottom: 16px; }}
    pre {{ background: #0f172a; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #1f2937; padding: 8px; text-align: left; }}
  </style>
</head>
<body>
  <h1>Trace {manifest.get("trace_id")}</h1>
  <div class=\"card\">
    <h2>Summary</h2>
    <table>
      <tr><th>Task</th><td>{manifest.get("task")}</td></tr>
      <tr><th>Provider</th><td>{manifest.get("provider")}</td></tr>
      <tr><th>Status</th><td>{metrics.get("status")}</td></tr>
      <tr><th>Events</th><td>{metrics.get("event_count")}</td></tr>
      <tr><th>Tool calls</th><td>{metrics.get("tool_call_count")}</td></tr>
      <tr><th>Errors</th><td>{metrics.get("error_count")}</td></tr>
      <tr><th>Duration (s)</th><td>{metrics.get("duration_s")}</td></tr>
    </table>
  </div>
  <div class=\"card\">
    <h2>Embedded JSON</h2>
    <pre id=\"payload\">{payload}</pre>
  </div>
</body>
</html>
"""


def _summarize(events: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    tool_call_count = sum(1 for event in events if event.get("type") == "tool_call")
    error_count = sum(1 for event in events if event.get("type") == "tool_error")
    status = next((event.get("status") for event in events if event.get("type") == "run_end"), "")
    duration_s = manifest.get("duration_s")
    if duration_s is None:
        duration_s = _duration(events)
    return {
        "event_count": len(events),
        "tool_call_count": tool_call_count,
        "error_count": error_count,
        "duration_s": duration_s,
        "status": status,
    }


def _duration(events: list[dict[str, Any]]) -> float | None:
    if not events:
        return None
    try:
        from datetime import datetime

        start_ts = events[0].get("ts")
        end_ts = events[-1].get("ts")
        if not start_ts or not end_ts:
            return None
        start = datetime.fromisoformat(start_ts)
        end = datetime.fromisoformat(end_ts)
        return max((end - start).total_seconds(), 0.0)
    except Exception:
        return None


def _tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = []
    for event in events:
        if event.get("type") == "tool_call":
            calls.append(
                {
                    "tool_name": event.get("tool_name"),
                    "arguments": event.get("arguments"),
                }
            )
    return calls


def _errors(events: list[dict[str, Any]]) -> list[str]:
    errors = []
    for event in events:
        if event.get("type") == "tool_error":
            errors.append(event.get("error", ""))
        if event.get("type") == "run_end" and event.get("status") == "error":
            errors.append(event.get("summary", ""))
    return [error for error in errors if error]


def _timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline = []
    for event in events:
        detail = event.get("summary") or event.get("content") or event.get("tool_name") or ""
        timeline.append(
            {
                "ts": event.get("ts"),
                "type": event.get("type"),
                "detail": str(detail)[:120],
            }
        )
    return timeline
