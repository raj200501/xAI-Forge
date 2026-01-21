from __future__ import annotations

import asyncio
from pathlib import Path

from xaiforge.agent.runner import stream_run


def test_stream_run_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    def on_event(payload: str) -> None:
        events.append(payload)

    manifest = asyncio.run(
        stream_run(
            task="Solve 2+2",
            provider_name="heuristic",
            root=Path("."),
            allow_net=False,
            on_event=on_event,
            plugins=[],
        )
    )
    trace_dir = tmp_path / ".xaiforge" / "traces"
    manifest_path = trace_dir / f"{manifest.trace_id}.manifest.json"
    report_path = trace_dir / f"{manifest.trace_id}.report.md"
    bench_path = tmp_path / ".xaiforge" / "bench" / f"{manifest.trace_id}.md"
    assert manifest_path.exists()
    assert report_path.exists()
    assert bench_path.exists()
    assert events
