from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from xaiforge.agent.runner import replay_trace, run_task
from xaiforge.trace_store import TraceReader, list_manifests

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    task: str = typer.Option(..., "--task", "-t"),
    root: Path = typer.Option(Path("."), "--root"),
    provider: str = typer.Option("heuristic", "--provider"),
    allow_net: bool = typer.Option(False, "--allow-net"),
) -> None:
    """Run a task and stream events to the console."""
    console.rule("xAI-Forge run")

    async def _run() -> None:
        import asyncio

        events = asyncio.Queue()

        def on_event(payload: str) -> None:
            events.put_nowait(payload)

        from xaiforge.agent.runner import stream_run

        runner = asyncio.create_task(
            stream_run(
                task=task,
                provider_name=provider,
                root=root,
                allow_net=allow_net,
                on_event=on_event,
            )
        )
        while not runner.done() or not events.empty():
            try:
                payload = await asyncio.wait_for(events.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            event = json.loads(payload)
            console.print(f"[bold cyan]{event['type']}[/bold cyan] {event.get('ts')}")
        manifest = await runner
        console.print(
            Panel(
                f"Trace: {manifest.trace_id}\nEvents: {manifest.event_count}\nHash: {manifest.final_hash}",
                title="Run complete",
            )
        )

    import asyncio

    asyncio.run(_run())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Start the API server."""
    console.print(Panel(f"Serving on http://{host}:{port}", title="xAI-Forge"))
    import uvicorn

    uvicorn.run("xaiforge.server:app", host=host, port=port, reload=False)


@app.command()
def replay(trace_id: str) -> None:
    """Replay a stored trace."""
    console.rule(f"Replaying {trace_id}")

    async def _run() -> None:
        events = []

        def on_event(payload: str) -> None:
            events.append(json.loads(payload))

        run_end = await replay_trace(trace_id, on_event)
        console.print(
            Panel(
                f"Integrity: {run_end.integrity_ok}\nHash: {run_end.final_hash}",
                title="Replay summary",
            )
        )

    import asyncio

    asyncio.run(_run())


@app.command()
def traces() -> None:
    """List stored traces."""
    manifests = list_manifests(Path(".xaiforge"))
    table = Table(title="Traces")
    table.add_column("Trace ID")
    table.add_column("Task")
    table.add_column("Provider")
    table.add_column("Started")
    for manifest in manifests:
        table.add_row(
            manifest.get("trace_id", ""),
            manifest.get("task", ""),
            manifest.get("provider", ""),
            manifest.get("started_at", ""),
        )
    console.print(table)


@app.command()
def doctor() -> None:
    """Check environment health."""
    table = Table(title="Doctor")
    table.add_column("Check")
    table.add_column("Result")

    table.add_row("Python", sys.version.split()[0])
    table.add_row("Node", shutil.which("node") or "missing")
    table.add_row("NPM", shutil.which("npm") or "missing")
    base_dir = Path(".xaiforge")
    try:
        base_dir.mkdir(exist_ok=True)
        table.add_row("Trace dir", "ok")
    except Exception as exc:
        table.add_row("Trace dir", f"error: {exc}")
    console.print(table)


@app.command()
def bench() -> None:
    """Run a benchmark suite of curated tasks."""
    tasks = [
        "Solve 23*47 and show your steps",
        "Compute 128/7 rounded to 2 decimals",
        "Search this repo for 'TODO' and summarize files",
        "Find all occurrences of 'trace' in README",
        "Calculate (12+7)*3",
        "Search this repo for 'xaiforge' and list files",
        "Compute 5^3 + 9",
        "Search this repo for 'FastAPI'",
        "Compute 1001-77",
        "Search this repo for 'React'",
    ]
    results = []
    import asyncio

    async def _run() -> None:
        for task in tasks:
            manifest = await run_task(task, "heuristic", Path("."), False)
            results.append(manifest)

    asyncio.run(_run())
    table = Table(title="Benchmark")
    table.add_column("Trace")
    table.add_column("Task")
    table.add_column("Events")
    for manifest in results:
        table.add_row(manifest.trace_id, manifest.task, str(manifest.event_count))
    console.print(table)


if __name__ == "__main__":
    app()
