from __future__ import annotations

from pathlib import Path

from xaiforge.events import RunEnd, RunStart, ToolCall
from xaiforge.query import parse_query, query_traces
from xaiforge.trace_store import TraceStore, TraceManifest


def test_parse_query():
    conditions = parse_query('type=tool_call AND tool~"search"')
    assert len(conditions) == 2
    assert conditions[0].field == "type"


def test_query_traces(tmp_path: Path) -> None:
    base_dir = tmp_path / ".xaiforge"
    trace_id = "t1"
    store = TraceStore(base_dir, trace_id)
    store.write_event(RunStart(trace_id=trace_id, task="task", provider="heuristic", root_dir="."))
    store.write_event(ToolCall(trace_id=trace_id, tool_name="search", arguments={"q": "TODO"}))
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

    results = query_traces(base_dir, "type=tool_call AND tool~search")
    assert results[trace_id] == 1
