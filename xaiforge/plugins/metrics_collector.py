from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from xaiforge.events import Event, RunEnd
from xaiforge.plugins.base import BasePlugin, PluginContext


@dataclass
class _MetricsState:
    event_counts: Counter[str] = field(default_factory=Counter)
    tool_calls: Counter[str] = field(default_factory=Counter)
    errors: int = 0


class MetricsCollector(BasePlugin):
    name = "metrics_collector"

    def __init__(self) -> None:
        self.state = _MetricsState()

    def on_event(self, context: PluginContext, event: Event) -> Event:
        self.state.event_counts[event.type] += 1
        if event.type == "tool_call":
            tool_name = getattr(event, "tool_name", "unknown")
            self.state.tool_calls[tool_name] += 1
        if event.type == "tool_error":
            self.state.errors += 1
        return event

    def on_run_end(self, context: PluginContext, event: Event) -> Event:
        if not isinstance(event, RunEnd):
            return event
        payload = {
            "trace_id": context.trace_id,
            "task": context.task,
            "provider": context.provider,
            "event_counts": dict(self.state.event_counts),
            "tool_calls": dict(self.state.tool_calls),
            "errors": self.state.errors,
            "status": event.status,
            "final_hash": event.final_hash,
        }
        metrics_path = context.base_dir / "traces" / f"{context.trace_id}.metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return event
