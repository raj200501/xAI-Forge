from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from xaiforge.agent.runner import run_task
from xaiforge.exporters import export_trace
from xaiforge.query import query_traces
from xaiforge.trace_store import TraceReader


@dataclass(frozen=True)
class DemoResult:
    trace_id: str
    export_path: Path
    bench_path: Path
    query_matches: int
    event_count: int


async def _run_demo_async(root: Path) -> DemoResult:
    demo_file = root / "demo.txt"
    demo_file.write_text("Hello from xAI-Forge demo.", encoding="utf-8")

    task = "Solve 23*47 and repo grep 'Hello'"
    manifest = await run_task(task=task, provider_name="heuristic", root=root, allow_net=False)
    export_path = export_trace(manifest.trace_id, "markdown", base_dir=Path(".xaiforge"))
    reader = TraceReader(Path(".xaiforge"), manifest.trace_id)
    event_count = sum(1 for _ in reader.iter_events())
    report_path = Path(".xaiforge") / "bench" / f"{manifest.trace_id}.md"
    results = query_traces(Path(".xaiforge"), "type=tool_call")
    return DemoResult(
        trace_id=manifest.trace_id,
        export_path=export_path,
        bench_path=report_path,
        query_matches=results.get(manifest.trace_id, 0),
        event_count=event_count,
    )


def run_demo(policy_path: Path | None = None) -> DemoResult:
    if policy_path is not None:
        os.environ["XAIFORGE_POLICY_FILE"] = str(policy_path)
    os.environ.setdefault("XAIFORGE_ENABLE_METRICS", "1")
    os.environ.setdefault("XAIFORGE_ENABLE_LOGGING", "1")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        return asyncio.run(_run_demo_async(root))
