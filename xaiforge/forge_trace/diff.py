from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xaiforge.trace_store import TraceReader


@dataclass
class TraceDiff:
    trace_a: str
    trace_b: str
    metrics: dict[str, dict[str, int | float]]

    def to_json(self) -> dict[str, Any]:
        return {
            "trace_a": self.trace_a,
            "trace_b": self.trace_b,
            "metrics": self.metrics,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Trace Diff: {self.trace_a} vs {self.trace_b}",
            "",
            "| Metric | A | B |",
            "| --- | --- | --- |",
        ]
        for key, values in self.metrics.items():
            lines.append(f"| {key} | {values['a']} | {values['b']} |")
        return "\n".join(lines)


def _collect_metrics(root: Path, trace_id: str) -> dict[str, int | float]:
    reader = TraceReader(root, trace_id)
    event_count = 0
    tool_calls = 0
    errors = 0
    usage_tokens = 0
    for line in reader.iter_events():
        payload = json.loads(line)
        event_count += 1
        if payload.get("type") == "tool_call":
            tool_calls += 1
        if payload.get("type") == "tool_error":
            errors += 1
        if payload.get("type") == "message":
            usage_tokens += len(str(payload.get("content", ""))) // 4
    manifest = reader.load_manifest()
    return {
        "event_count": event_count,
        "tool_calls": tool_calls,
        "errors": errors,
        "usage_tokens": usage_tokens,
        "duration_s": float(manifest.get("duration_s", 0.0)) if "duration_s" in manifest else 0.0,
    }


def diff_traces(root: Path, trace_a: str, trace_b: str) -> TraceDiff:
    metrics_a = _collect_metrics(root, trace_a)
    metrics_b = _collect_metrics(root, trace_b)
    metrics = {key: {"a": metrics_a[key], "b": metrics_b[key]} for key in metrics_a}
    return TraceDiff(trace_a=trace_a, trace_b=trace_b, metrics=metrics)
