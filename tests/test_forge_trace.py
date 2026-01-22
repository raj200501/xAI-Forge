import json
from pathlib import Path

from xaiforge.events import Message, RunEnd, RunStart
from xaiforge.forge_trace import diff_traces, replay_summary, verify_trace
from xaiforge.trace_store import TraceManifest, TraceStore


def _write_trace(base: Path, trace_id: str, task: str) -> None:
    store = TraceStore(base, trace_id)
    store.write_event(RunStart(trace_id=trace_id, task=task, provider="mock", root_dir=str(base)))
    store.write_event(Message(trace_id=trace_id, role="assistant", content=f"hello {task}"))
    run_end = RunEnd(trace_id=trace_id, summary="done")
    run_end.final_hash = store.hasher.hexdigest
    run_end.event_count = store.event_count + 1
    store.write_event(run_end)
    store.close()
    store.write_manifest(
        TraceManifest(
            trace_id=trace_id,
            started_at="2024-01-01T00:00:00+00:00",
            ended_at="2024-01-01T00:00:01+00:00",
            root_dir=str(base),
            provider="mock",
            task=task,
            final_hash=store.hasher.hexdigest,
            event_count=store.event_count,
        )
    )


def test_verify_trace(tmp_path: Path):
    base = tmp_path / ".xaiforge"
    base.mkdir()
    _write_trace(base, "trace-a", "task-a")
    result = verify_trace(base, "trace-a")
    summary = replay_summary(result)
    assert summary["integrity_ok"] is True
    assert summary["event_count"] >= 2


def test_diff_traces(tmp_path: Path):
    base = tmp_path / ".xaiforge"
    base.mkdir()
    _write_trace(base, "trace-a", "task-a")
    _write_trace(base, "trace-b", "task-b")
    diff = diff_traces(base, "trace-a", "trace-b")
    payload = diff.to_json()
    assert payload["trace_a"] == "trace-a"
    assert "event_count" in payload["metrics"]
    assert json.loads(json.dumps(payload))
