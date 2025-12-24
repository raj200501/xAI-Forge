from __future__ import annotations

from pathlib import Path

from xaiforge.events import Message, RunEnd, RunStart, ToolCall
from xaiforge.plugins.base import PluginContext
from xaiforge.plugins.metrics_collector import MetricsCollector
from xaiforge.plugins.redactor import Redactor


def test_redactor_masks_secrets() -> None:
    plugin = Redactor()
    context = PluginContext(
        trace_id="t1",
        base_dir=Path("."),
        task="task",
        provider="heuristic",
        root=Path("."),
        started_at="now",
    )
    event = Message(
        trace_id="t1",
        role="assistant",
        content="Contact me at test@example.com with token sk-1234567890123456",
    )
    redacted = plugin.on_event(context, event)
    assert "[redacted-email]" in redacted.content
    assert "[redacted-token]" in redacted.content


def test_metrics_collector_writes_file(tmp_path: Path) -> None:
    plugin = MetricsCollector()
    context = PluginContext(
        trace_id="t1",
        base_dir=tmp_path,
        task="task",
        provider="heuristic",
        root=Path("."),
        started_at="now",
    )
    plugin.on_run_start(context, RunStart(trace_id="t1", task="task", provider="heuristic", root_dir="."))
    plugin.on_event(context, ToolCall(trace_id="t1", tool_name="search", arguments={"q": "x"}))
    run_end = RunEnd(trace_id="t1", summary="done", status="ok")
    plugin.on_run_end(context, run_end)
    metrics_path = tmp_path / "traces" / "t1.metrics.json"
    assert metrics_path.exists()
