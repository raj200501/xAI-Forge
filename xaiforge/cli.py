from __future__ import annotations

# ruff: noqa: I001

import json
import shutil
import sys
import time
import webbrowser
from pathlib import Path

from xaiforge.agent.runner import replay_trace, run_task
from xaiforge.compat import typer
from xaiforge.compat.rich import Console, Panel, Table
from xaiforge.exporters import export_latest, export_trace
from xaiforge.plugins.registry import available_plugins
from xaiforge.query import query_traces
from xaiforge.trace_store import TraceManifest, TraceReader, list_manifests
from xaiforge.forge_experiments.cli import experiment_app
from xaiforge.forge_perf.cli import perf_app
from xaiforge.forge_index.cli import index_app

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    task: str = typer.Option(..., "--task", "-t"),  # noqa: B008
    root: Path = typer.Option(Path("."), "--root"),  # noqa: B008
    provider: str = typer.Option("heuristic", "--provider"),  # noqa: B008
    allow_net: bool = typer.Option(False, "--allow-net"),  # noqa: B008
    plugins: str = typer.Option("", "--plugins", help="Comma-separated plugin list"),  # noqa: B008
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
                plugins=_parse_plugins(plugins),
                on_event=on_event,
            )
        )
        while not runner.done() or not events.empty():
            try:
                payload = await asyncio.wait_for(events.get(), timeout=0.1)
            except TimeoutError:
                continue
            event = json.loads(payload)
            console.print(f"[bold cyan]{event['type']}[/bold cyan] {event.get('ts')}")
        manifest = await runner
        console.print(
            Panel(
                (
                    f"Trace: {manifest.trace_id}\n"
                    f"Events: {manifest.event_count}\n"
                    f"Hash: {manifest.final_hash}"
                ),
                title="Run complete",
            )
        )

    import asyncio

    asyncio.run(_run())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),  # noqa: B008
    port: int = typer.Option(8000, "--port"),  # noqa: B008
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
def export(
    trace_id: str = typer.Argument(..., help="Trace ID or 'latest'"),  # noqa: B008
    format: str = typer.Option("markdown", "--format", "-f"),  # noqa: B008
    output: Path | None = typer.Option(None, "--output", "-o"),  # noqa: B008
) -> None:
    """Export a trace in markdown, html, or json format."""
    export_format = format.lower()
    if trace_id == "latest":
        path = export_latest(export_format)
    else:
        path = export_trace(trace_id, export_format, output)
    console.print(Panel(f"Exported to {path}", title="xAI-Forge export"))


@app.command()
def query(expr: str = typer.Argument(..., help="Query expression")) -> None:
    """Search events across traces with a minimal DSL."""
    results = query_traces(Path(".xaiforge"), expr)
    table = Table(title=f"Query: {expr}")
    table.add_column("Trace ID")
    table.add_column("Matches")
    for trace_id, count in sorted(results.items(), key=lambda item: item[1], reverse=True):
        table.add_row(trace_id, str(count))
    console.print(table)


@app.command("query-fast")
def query_fast(expr: str = typer.Argument(..., help="Query expression")) -> None:
    """Search events using the fast index backend."""
    from xaiforge.forge_index.query import fast_query

    results = fast_query(Path(".xaiforge"), expr)
    table = Table(title=f"Fast Query: {expr}")
    table.add_column("Trace ID")
    table.add_column("Matches")
    for trace_id, count in sorted(results.items(), key=lambda item: item[1], reverse=True):
        table.add_row(trace_id, str(count))
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
def ui(
    open_browser: bool = typer.Option(True, "--open/--no-open"),
    url: str = typer.Option("http://127.0.0.1:5173", "--url"),
) -> None:
    """Open the web UI in a browser and print local dev instructions."""
    console.rule("xAI-Forge UI")
    console.print(
        Panel(
            "Start the API and UI in separate terminals:\n\n"
            "[bold]Terminal 1[/bold]\n"
            "python -m xaiforge serve\n\n"
            "[bold]Terminal 2[/bold]\n"
            "cd web && npm install && npm run dev\n\n"
            f"Then open [bold]{url}[/bold]",
            title="UI Quickstart",
        )
    )
    if open_browser:
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:
            console.print(f"[yellow]Unable to open browser:[/yellow] {exc}")


@app.command()
def gateway_test(
    stream: bool = typer.Option(False, "--stream"),  # noqa: B008
    batch: bool = typer.Option(False, "--batch"),  # noqa: B008
) -> None:
    """Exercise the Forge Model Gateway with mock provider."""
    from xaiforge.forge_gateway import GatewayConfig, ModelGateway
    from xaiforge.forge_gateway.models import ModelMessage, ModelRequest

    config = GatewayConfig()
    config.batch.enabled = batch
    gateway = ModelGateway(config=config)
    request = ModelRequest(messages=[ModelMessage(role="user", content="gateway test")])
    if stream:

        async def _run() -> None:
            async for event in gateway.stream(request):
                console.print(f"[cyan]{event.chunk.text}[/cyan]", end="")
            console.print()

        import asyncio

        asyncio.run(_run())
    else:
        import asyncio

        result = asyncio.run(gateway.generate(request))
        console.print(Panel(result.response.to_json(), title="Gateway response"))


@app.command()
def eval(
    dataset: str = typer.Option("trace_ops", "--dataset"),  # noqa: B008
    gate: bool = typer.Option(False, "--gate"),  # noqa: B008
) -> None:
    """Run Forge evals and optionally enforce regression gates."""
    from xaiforge.forge_evals.runner import gate_report, run_eval

    dataset_path = Path("xaiforge/forge_evals/datasets") / f"{dataset}.jsonl"
    report_dir = Path("reports/evals")
    report = run_eval(dataset_path, report_dir)
    console.print(Panel(f"Pass rate: {report.pass_rate:.2%}", title="Evals"))
    if gate:
        baseline_path = Path("xaiforge/forge_evals/baseline.json")
        gate_report(report, baseline_path)
        console.print(Panel("Eval gate passed", title="Evals"))


@app.command()
def replay_verify(trace_id: str = typer.Argument(...)) -> None:
    """Verify trace integrity and emit a summary report."""
    from xaiforge.forge_trace import replay_summary, verify_trace

    result = verify_trace(Path(".xaiforge"), trace_id)
    console.print(Panel(json.dumps(replay_summary(result), indent=2), title="Replay verify"))


@app.command()
def diff(
    trace_a: str = typer.Argument(...),  # noqa: B008
    trace_b: str = typer.Argument(...),  # noqa: B008
) -> None:
    """Diff two traces and output a summary."""
    from xaiforge.forge_trace import diff_traces

    diff_result = diff_traces(Path(".xaiforge"), trace_a, trace_b)
    output_dir = Path("reports/trace-diff")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{trace_a}_vs_{trace_b}.json"
    json_path.write_text(json.dumps(diff_result.to_json(), indent=2), encoding="utf-8")
    md_path = output_dir / f"{trace_a}_vs_{trace_b}.md"
    md_path.write_text(diff_result.to_markdown(), encoding="utf-8")
    console.print(Panel(f"Diff saved to {json_path}", title="Trace diff"))


@app.command("replay_verify")
def replay_verify_compat(trace_id: str = typer.Argument(...)) -> None:
    """Compatibility command for replay_verify."""
    replay_verify(trace_id)


@app.command()
def demo(
    policy: Path | None = typer.Option(None, "--policy", help="Path to policy JSON"),  # noqa: B008
) -> None:
    """Run a local demo in a temporary directory."""
    from xaiforge.demo import run_demo

    console.rule("xAI-Forge demo")
    result = run_demo(policy)
    console.print(
        Panel(
            f"Trace: {result.trace_id}\n"
            f"Events: {result.event_count}\n"
            f"Export: {result.export_path}\n"
            f"Bench: {result.bench_path}\n"
            f"Query matches: {result.query_matches}",
            title="Demo complete",
        )
    )


@app.command()
def policy_summary(
    policy: Path = typer.Option(..., "--policy", help="Path to policy JSON"),  # noqa: B008
) -> None:
    """Summarize a policy file."""
    from xaiforge.policy.cli import load_policy_config, render_policy_summary, summarize_policy

    config = load_policy_config(policy)
    summary = summarize_policy(config)
    console.print(Panel(render_policy_summary(summary), title="Policy"))


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
            started = time.perf_counter()
            manifest = await run_task(task, "heuristic", Path("."), False, [])
            duration = time.perf_counter() - started
            tool_calls = _count_tool_calls(manifest.trace_id)
            results.append((manifest, duration, tool_calls))

    asyncio.run(_run())
    table = Table(title="Benchmark")
    table.add_column("Trace")
    table.add_column("Task")
    table.add_column("Events")
    table.add_column("Duration (s)")
    table.add_column("Tool calls")
    for manifest, duration, tool_calls in results:
        table.add_row(
            manifest.trace_id,
            manifest.task,
            str(manifest.event_count),
            f"{duration:.2f}",
            str(tool_calls),
        )
    console.print(table)
    _write_benchmark_summary(results)


def _count_tool_calls(trace_id: str) -> int:
    reader = TraceReader(Path(".xaiforge"), trace_id)
    count = 0
    for line in reader.iter_events():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "tool_call":
            count += 1
    return count


def _write_benchmark_summary(results: list[tuple[TraceManifest, float, int]]) -> None:
    bench_dir = Path(".xaiforge") / "bench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark Summary\n",
        "\n",
        "| Trace | Task | Events | Duration (s) | Tool Calls |\n",
        "| --- | --- | --- | --- | --- |\n",
    ]
    for manifest, duration, tool_calls in results:
        lines.append(
            f"| {manifest.trace_id} | {manifest.task} | {manifest.event_count} |"
            f" {duration:.2f} | {tool_calls} |\n"
        )
    (bench_dir / "latest.md").write_text("".join(lines), encoding="utf-8")


def _parse_plugins(value: str) -> list[str]:
    if not value.strip():
        return []
    plugins = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [name for name in plugins if name not in available_plugins()]
    if unknown:
        raise typer.BadParameter(
            f"Unknown plugins: {', '.join(unknown)}. Available: {', '.join(available_plugins())}"
        )
    return plugins


app.add_typer(experiment_app, name="experiment")
app.add_typer(perf_app, name="perf")
app.add_typer(index_app, name="index")


if __name__ == "__main__":
    app()
