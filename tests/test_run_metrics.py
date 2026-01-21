from __future__ import annotations

from pathlib import Path

from xaiforge.observability.metrics import MetricSerializer, MetricsRegistry
from xaiforge.observability.run_metrics import RunMetrics


def test_metrics_registry_snapshot() -> None:
    registry = MetricsRegistry()
    registry.counter("events.total").inc(3)
    registry.gauge("run.duration_s").set(1.5)
    with registry.timer("phase"):
        pass
    snapshot = registry.snapshot()
    assert snapshot.counters["events.total"] == 3
    assert snapshot.gauges["run.duration_s"] == 1.5
    assert "phase" in snapshot.timers


def test_metric_serializer_roundtrip() -> None:
    registry = MetricsRegistry()
    registry.counter("tools.total").inc(2)
    snapshot = registry.snapshot()
    serializer = MetricSerializer()
    payload = serializer.to_dict(snapshot)
    restored = serializer.from_dict(payload)
    assert restored.counters["tools.total"] == 2


def test_run_metrics_write(tmp_path: Path) -> None:
    base_dir = tmp_path / ".xaiforge"
    metrics = RunMetrics(trace_id="trace-123")
    metrics.record_event("run_start")
    metrics.record_tool("calc", "ok")
    path = metrics.write(base_dir)
    assert path.exists()
    payload = path.read_text(encoding="utf-8")
    assert "trace-123" in payload
