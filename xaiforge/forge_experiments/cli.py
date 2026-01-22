from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xaiforge.compat import typer
from xaiforge.compat.rich import Console, Panel, Table
from xaiforge.forge_experiments.models import ExperimentConfig, ExperimentRequestTemplate
from xaiforge.forge_experiments.runner import (
    ExperimentGateError,
    gate_experiment,
    list_experiments,
    run_experiment,
    save_experiment_artifacts,
)
from xaiforge.forge_gateway.models import ModelMessage, ToolDefinition

experiment_app = typer.Typer(add_completion=False)
console = Console()


def _load_request(task: str | None, request_json: Path | None) -> ExperimentRequestTemplate:
    if request_json:
        payload = json.loads(request_json.read_text(encoding="utf-8"))
        messages = [ModelMessage(**message) for message in payload.get("messages", [])]
        tools = [ToolDefinition(**tool) for tool in payload.get("tools", [])]
        return ExperimentRequestTemplate(
            messages=messages,
            tools=tools,
            tags=payload.get("tags", []),
            metadata=payload.get("metadata", {}),
            temperature=payload.get("temperature", 0.2),
            max_tokens=payload.get("max_tokens", 512),
            seed=payload.get("seed"),
            stop=payload.get("stop"),
        )
    if not task:
        raise typer.BadParameter("Provide --task or --request")
    return ExperimentRequestTemplate(messages=[ModelMessage(role="user", content=task)])


@experiment_app.command("run")
def run_command(
    mode: str = typer.Option("ab", "--mode"),  # noqa: B008
    providers: str = typer.Option("mock", "--providers"),  # noqa: B008
    task: str | None = typer.Option(None, "--task"),  # noqa: B008
    request: Path | None = typer.Option(None, "--request"),  # noqa: B008
    max_concurrency: int = typer.Option(4, "--max-concurrency"),  # noqa: B008
    timeout_s: float = typer.Option(30.0, "--timeout"),  # noqa: B008
) -> None:
    """Run a Forge experiment across providers."""
    config = ExperimentConfig.create(
        experiment_id=_new_experiment_id(),
        mode=mode,  # type: ignore[arg-type]
        providers=[item.strip() for item in providers.split(",") if item.strip()],
        request_template=_load_request(task, request),
        max_concurrency=max_concurrency,
        timeout_s=timeout_s,
    )
    result = run_experiment(config)
    manifest = save_experiment_artifacts(config, result)
    console.print(
        Panel(
            f"Experiment {manifest.experiment_id} complete\nReport: {manifest.report_path}",
            title="Forge Experiments",
        )
    )


@experiment_app.command("list")
def list_command() -> None:
    """List stored experiments."""
    table = Table(title="Experiments")
    table.add_column("Experiment")
    table.add_column("Mode")
    table.add_column("Providers")
    table.add_column("Status")
    table.add_column("Stability")
    for manifest in list_experiments():
        summary = manifest.summary
        table.add_row(
            manifest.experiment_id,
            summary.mode,
            ", ".join(summary.providers),
            summary.status,
            f"{summary.stability_score:.2f}" if summary.stability_score is not None else "-",
        )
    console.print(table)


@experiment_app.command("show")
def show_command(experiment_id: str) -> None:
    """Show a stored experiment report."""
    report_path = Path("reports") / "experiments" / f"{experiment_id}.json"
    if not report_path.exists():
        raise typer.BadParameter("Report not found")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    console.print(Panel(json.dumps(payload, indent=2), title=f"Experiment {experiment_id}"))


@experiment_app.command("gate")
def gate_command(
    experiment_id: str,
    stability_min: float = typer.Option(0.7, "--stability-min"),  # noqa: B008
    max_latency_delta_ms: int = typer.Option(500, "--max-latency-delta"),  # noqa: B008
    max_error_rate: float = typer.Option(0.1, "--max-error-rate"),  # noqa: B008
) -> None:
    """Gate an experiment report based on thresholds."""
    try:
        summary = gate_experiment(
            experiment_id,
            stability_min=stability_min,
            max_latency_delta_ms=max_latency_delta_ms,
            max_error_rate=max_error_rate,
        )
    except ExperimentGateError as exc:
        raise typer.Exit(code=1) from exc
    console.print(Panel(json.dumps(summary.to_dict(), indent=2), title="Experiment gate"))


def _new_experiment_id() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("exp%Y%m%d%H%M%S%f")


_unused_any: Any | None = None
