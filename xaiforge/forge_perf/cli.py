from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import json
from pathlib import Path

from xaiforge.compat import typer
from xaiforge.compat.rich import Console, Panel
from xaiforge.forge_perf.gate import PerfGateError, gate_performance
from xaiforge.forge_perf.load import run_load
from xaiforge.forge_perf.runner import run_bench

perf_app = typer.Typer(add_completion=False)
console = Console()


@perf_app.command("bench")
def bench_command(
    suite: str = typer.Option("quick", "--suite"),  # noqa: B008
    provider: str = typer.Option("mock", "--provider"),  # noqa: B008
    max_concurrency: int = typer.Option(4, "--max-concurrency"),  # noqa: B008
    timeout_s: float = typer.Option(30.0, "--timeout"),  # noqa: B008
) -> None:
    """Run a perf benchmark suite."""
    result = run_bench(suite=suite, provider=provider, max_concurrency=max_concurrency, timeout_s=timeout_s)
    console.print(Panel(json.dumps(result.to_dict(), indent=2), title="Perf bench"))


@perf_app.command("load")
def load_command(
    duration_s: int = typer.Option(10, "--duration"),  # noqa: B008
    concurrency: int = typer.Option(10, "--concurrency"),  # noqa: B008
    ramp_up_s: int = typer.Option(0, "--ramp-up"),  # noqa: B008
    request_rate: float = typer.Option(5.0, "--request-rate"),  # noqa: B008
    provider: str = typer.Option("mock", "--provider"),  # noqa: B008
    timeout_s: float = typer.Option(30.0, "--timeout"),  # noqa: B008
) -> None:
    """Run a load test."""
    result = run_load(
        duration_s=duration_s,
        concurrency=concurrency,
        ramp_up_s=ramp_up_s,
        request_rate=request_rate,
        provider=provider,
        timeout_s=timeout_s,
    )
    console.print(Panel(json.dumps(result.to_dict(), indent=2), title="Perf load"))


@perf_app.command("gate")
def gate_command(
    baseline: Path = typer.Option(Path("xaiforge/forge_perf/baseline.json"), "--baseline"),  # noqa: B008
) -> None:
    """Gate perf metrics against a baseline."""
    latest = _load_latest_report()
    if not latest:
        raise typer.BadParameter("No perf reports available")
    metrics = latest["metrics"]
    from xaiforge.forge_perf.metrics import PerfMetrics

    perf_metrics = PerfMetrics(
        latencies_ms=metrics.get("latencies_ms", []),
        errors=metrics.get("errors", 0),
        total=metrics.get("total", 0),
        ttft_ms=metrics.get("ttft_ms", []),
    )
    try:
        result = gate_performance(perf_metrics, baseline)
    except PerfGateError as exc:
        raise typer.Exit(code=1) from exc
    console.print(Panel(json.dumps(result, indent=2), title="Perf gate"))


def _load_latest_report() -> dict | None:
    reports_dir = Path("reports") / "perf"
    if not reports_dir.exists():
        return None
    reports = sorted(reports_dir.glob("*.json"))
    if not reports:
        return None
    return json.loads(reports[-1].read_text(encoding="utf-8"))
