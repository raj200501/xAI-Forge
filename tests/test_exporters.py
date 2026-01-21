from __future__ import annotations

import json
from pathlib import Path

from xaiforge.events import RunEnd, RunStart
from xaiforge.exporters import export_trace
from xaiforge.trace_store import TraceManifest, TraceStore


def test_export_trace_markdown(tmp_path: Path) -> None:
    base_dir = tmp_path / ".xaiforge"
    trace_id = "t1"
    store = TraceStore(base_dir, trace_id)
    store.write_event(RunStart(trace_id=trace_id, task="task", provider="heuristic", root_dir="."))
    store.write_event(RunEnd(trace_id=trace_id, summary="done", status="ok"))
    store.close()
    manifest = TraceManifest(
        trace_id=trace_id,
        started_at="a",
        ended_at="b",
        root_dir=".",
        provider="heuristic",
        task="task",
        final_hash=store.hasher.hexdigest,
        event_count=store.event_count,
    )
    store.write_manifest(manifest)

    output = export_trace(trace_id, "markdown", base_dir=base_dir)
    content = output.read_text(encoding="utf-8")
    assert "# Trace" in content
    assert "## Timeline" in content


def test_export_trace_json(tmp_path: Path) -> None:
    base_dir = tmp_path / ".xaiforge"
    trace_id = "t2"
    store = TraceStore(base_dir, trace_id)
    store.write_event(RunStart(trace_id=trace_id, task="task", provider="heuristic", root_dir="."))
    store.write_event(RunEnd(trace_id=trace_id, summary="done", status="ok"))
    store.close()
    manifest = TraceManifest(
        trace_id=trace_id,
        started_at="a",
        ended_at="b",
        root_dir=".",
        provider="heuristic",
        task="task",
        final_hash=store.hasher.hexdigest,
        event_count=store.event_count,
    )
    store.write_manifest(manifest)

    output = export_trace(trace_id, "json", base_dir=base_dir)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["manifest"]["trace_id"] == trace_id
