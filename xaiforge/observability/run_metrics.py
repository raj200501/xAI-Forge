from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xaiforge.observability.metrics import MetricSerializer, MetricsRegistry


@dataclass
class RunMetrics:
    trace_id: str
    registry: MetricsRegistry = field(default_factory=MetricsRegistry)
    _start_ts: float = field(default_factory=time.perf_counter)

    def record_event(self, event_type: str) -> None:
        self.registry.counter("events.total").inc()
        self.registry.counter(f"events.{event_type}").inc()

    def record_tool(self, tool_name: str, outcome: str) -> None:
        self.registry.counter("tools.total").inc()
        self.registry.counter(f"tools.{tool_name}").inc()
        self.registry.counter(f"tools.outcome.{outcome}").inc()

    def record_duration(self) -> None:
        duration = time.perf_counter() - self._start_ts
        self.registry.gauge("run.duration_s").set(duration)

    def snapshot(self) -> dict[str, Any]:
        serializer = MetricSerializer()
        return serializer.to_dict(self.registry.snapshot())

    def write(self, base_dir: Path) -> Path:
        self.record_duration()
        metrics_dir = base_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        path = metrics_dir / f"{self.trace_id}.json"
        payload = {
            "trace_id": self.trace_id,
            "metrics": self.snapshot(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
