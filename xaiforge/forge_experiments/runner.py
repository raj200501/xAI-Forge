from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import asyncio
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from xaiforge.forge_experiments.compare import compare_text, compare_tool_calls
from xaiforge.forge_experiments.models import (
    ExperimentComparison,
    ExperimentConfig,
    ExperimentManifest,
    ExperimentMode,
    ExperimentProviderResult,
    ExperimentRequestTemplate,
    ExperimentResult,
    ExperimentRunSummary,
)
from xaiforge.forge_gateway import GatewayConfig, ModelGateway
from xaiforge.forge_gateway.models import ModelRequest


@dataclass(frozen=True)
class ExperimentGateError(Exception):
    message: str
    summary: ExperimentRunSummary

    def __str__(self) -> str:
        return self.message


class ExperimentRunner:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(".xaiforge")

    async def run(self, config: ExperimentConfig) -> ExperimentResult:
        template = config.request_template
        if not template:
            raise ValueError("Experiment requires a request template")
        request_id = _build_request_id(config.experiment_id)
        started_at = datetime.now(UTC).isoformat()
        if config.mode == "ab":
            results = await self._run_ab(config, template, request_id)
            comparison = _build_comparison(results[0], results[1])
            primary = results[0]
            secondary = results[1]
        elif config.mode == "shadow":
            primary, secondary, results = await self._run_shadow(config, template, request_id)
            comparison = _build_comparison(primary, secondary)
        elif config.mode == "canary":
            primary, secondary, results = await self._run_canary(config, template, request_id)
            comparison = _build_comparison(primary, secondary) if secondary else None
        elif config.mode == "fallback":
            primary, results = await self._run_fallback(config, template, request_id)
            secondary = results[1] if len(results) > 1 else None
            comparison = _build_comparison(primary, secondary) if secondary else None
        else:
            raise ValueError(f"Unknown experiment mode: {config.mode}")
        ended_at = datetime.now(UTC).isoformat()
        errors = [result.error for result in results if result.error]
        return ExperimentResult(
            experiment_id=config.experiment_id,
            mode=config.mode,
            request_id=request_id,
            primary=primary,
            secondary=secondary,
            all_results=results,
            comparison=comparison,
            errors=errors,
            started_at=started_at,
            ended_at=ended_at,
        )

    async def _run_ab(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        request_id: str,
    ) -> list[ExperimentProviderResult]:
        providers = _require_providers(config.providers, 2)
        results = await self._run_providers(config, template, providers, request_id)
        return results

    async def _run_shadow(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        request_id: str,
    ) -> tuple[ExperimentProviderResult, ExperimentProviderResult, list[ExperimentProviderResult]]:
        providers = _require_providers(config.providers, 2)
        primary_provider = providers[0]
        shadow_provider = providers[1]
        results = await self._run_providers(config, template, [primary_provider, shadow_provider], request_id)
        return results[0], results[1], results

    async def _run_canary(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        request_id: str,
    ) -> tuple[ExperimentProviderResult, ExperimentProviderResult | None, list[ExperimentProviderResult]]:
        providers = _require_providers(config.providers, 2)
        primary_provider = providers[0]
        canary_provider = providers[1]
        rng = random.Random(_stable_seed(config.experiment_id))
        send_canary = rng.random() < config.traffic_split
        if send_canary:
            results = await self._run_providers(config, template, [primary_provider, canary_provider], request_id)
            return results[0], results[1], results
        results = await self._run_providers(config, template, [primary_provider], request_id)
        return results[0], None, results

    async def _run_fallback(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        request_id: str,
    ) -> tuple[ExperimentProviderResult, list[ExperimentProviderResult]]:
        providers = _require_providers(config.providers, 1)
        results: list[ExperimentProviderResult] = []
        errors: list[str] = []
        for provider in providers:
            result = await self._run_provider(config, template, provider, request_id)
            results.append(result)
            if not result.error:
                return result, results
            errors.append(result.error)
        raise RuntimeError("All fallback providers failed: " + ", ".join(errors))

    async def _run_providers(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        providers: list[str],
        request_id: str,
    ) -> list[ExperimentProviderResult]:
        semaphore = asyncio.Semaphore(max(1, config.max_concurrency))

        async def _wrapped(provider: str) -> ExperimentProviderResult:
            async with semaphore:
                return await self._run_provider(config, template, provider, request_id)

        tasks = [asyncio.create_task(_wrapped(provider)) for provider in providers]
        return await asyncio.gather(*tasks)

    async def _run_provider(
        self,
        config: ExperimentConfig,
        template: ExperimentRequestTemplate,
        provider: str,
        request_id: str,
    ) -> ExperimentProviderResult:
        if provider.startswith("fail"):
            return ExperimentProviderResult(
                provider=provider,
                model="",
                text="",
                tool_calls=[],
                latency_ms=0,
                usage={},
                error="Injected failure",
            )
        gateway_config = GatewayConfig()
        gateway_config.provider = provider
        gateway_config.timeout_s = config.timeout_s
        gateway = ModelGateway(config=gateway_config)
        request = template.to_request(request_id=request_id)
        try:
            result = await gateway.generate(request)
            response = result.response
            return ExperimentProviderResult(
                provider=provider,
                model=response.model,
                text=response.text,
                tool_calls=[call.__dict__ for call in response.tool_calls],
                latency_ms=response.latency_ms,
                usage=response.usage.__dict__,
                error=None,
            )
        except Exception as exc:
            return ExperimentProviderResult(
                provider=provider,
                model="",
                text="",
                tool_calls=[],
                latency_ms=0,
                usage={},
                error=str(exc),
            )


def run_experiment(config: ExperimentConfig, base_dir: Path | None = None) -> ExperimentResult:
    runner = ExperimentRunner(base_dir=base_dir)
    return asyncio.run(runner.run(config))


def list_experiments(base_dir: Path | None = None) -> list[ExperimentManifest]:
    base_dir = base_dir or Path(".xaiforge")
    exp_dir = base_dir / "experiments"
    if not exp_dir.exists():
        return []
    manifests = []
    for path in exp_dir.glob("*.manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        summary = ExperimentRunSummary(
            experiment_id=payload["summary"]["experiment_id"],
            created_at=payload["summary"]["created_at"],
            mode=payload["summary"]["mode"],
            providers=payload["summary"].get("providers", []),
            request_id=payload["summary"].get("request_id", ""),
            status=payload["summary"].get("status", "unknown"),
            stability_score=payload["summary"].get("stability_score"),
            latency_delta_ms=payload["summary"].get("latency_delta_ms"),
            error_rate=payload["summary"].get("error_rate", 0.0),
        )
        manifests.append(
            ExperimentManifest(
                experiment_id=payload["experiment_id"],
                created_at=payload["created_at"],
                report_path=payload["report_path"],
                config_path=payload["config_path"],
                summary=summary,
            )
        )
    manifests.sort(key=lambda item: item.created_at, reverse=True)
    return manifests


def load_experiment_manifest(experiment_id: str, base_dir: Path | None = None) -> ExperimentManifest:
    base_dir = base_dir or Path(".xaiforge")
    manifest_path = base_dir / "experiments" / f"{experiment_id}.manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = ExperimentRunSummary(
        experiment_id=payload["summary"]["experiment_id"],
        created_at=payload["summary"]["created_at"],
        mode=payload["summary"]["mode"],
        providers=payload["summary"].get("providers", []),
        request_id=payload["summary"].get("request_id", ""),
        status=payload["summary"].get("status", "unknown"),
        stability_score=payload["summary"].get("stability_score"),
        latency_delta_ms=payload["summary"].get("latency_delta_ms"),
        error_rate=payload["summary"].get("error_rate", 0.0),
    )
    return ExperimentManifest(
        experiment_id=payload["experiment_id"],
        created_at=payload["created_at"],
        report_path=payload["report_path"],
        config_path=payload["config_path"],
        summary=summary,
    )


def gate_experiment(
    experiment_id: str,
    base_dir: Path | None = None,
    stability_min: float = 0.7,
    max_latency_delta_ms: int = 500,
    max_error_rate: float = 0.1,
) -> ExperimentRunSummary:
    manifest = load_experiment_manifest(experiment_id, base_dir)
    summary = manifest.summary
    if summary.stability_score is not None and summary.stability_score < stability_min:
        raise ExperimentGateError(
            f"Experiment {experiment_id} stability score {summary.stability_score:.2f} below {stability_min:.2f}",
            summary,
        )
    if summary.latency_delta_ms is not None and summary.latency_delta_ms > max_latency_delta_ms:
        raise ExperimentGateError(
            f"Experiment {experiment_id} latency delta {summary.latency_delta_ms}ms above {max_latency_delta_ms}ms",
            summary,
        )
    if summary.error_rate > max_error_rate:
        raise ExperimentGateError(
            f"Experiment {experiment_id} error rate {summary.error_rate:.2%} above {max_error_rate:.2%}",
            summary,
        )
    return summary


def save_experiment_artifacts(
    config: ExperimentConfig,
    result: ExperimentResult,
    base_dir: Path | None = None,
) -> ExperimentManifest:
    base_dir = base_dir or Path(".xaiforge")
    exp_dir = base_dir / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path("reports") / "experiments"
    reports_dir.mkdir(parents=True, exist_ok=True)
    config_path = exp_dir / f"{config.experiment_id}.config.json"
    config_path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    report_path = reports_dir / f"{config.experiment_id}.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    md_path = reports_dir / f"{config.experiment_id}.md"
    md_path.write_text(render_markdown_report(config, result), encoding="utf-8")
    summary = summarize_result(config, result)
    manifest = ExperimentManifest(
        experiment_id=config.experiment_id,
        created_at=config.created_at,
        report_path=str(report_path),
        config_path=str(config_path),
        summary=summary,
    )
    manifest_path = exp_dir / f"{config.experiment_id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return manifest


def summarize_result(config: ExperimentConfig, result: ExperimentResult) -> ExperimentRunSummary:
    error_rate = len(result.errors) / max(len(result.all_results), 1)
    stability_score = None
    latency_delta_ms = None
    status = "ok" if not result.errors else "partial"
    if result.comparison:
        stability_score = result.comparison.stability_score
        latency_delta_ms = result.comparison.latency_delta_ms
    if result.errors and len(result.errors) == len(result.all_results):
        status = "error"
    return ExperimentRunSummary(
        experiment_id=config.experiment_id,
        created_at=config.created_at,
        mode=config.mode,
        providers=list(config.providers),
        request_id=result.request_id,
        status=status,
        stability_score=stability_score,
        latency_delta_ms=latency_delta_ms,
        error_rate=error_rate,
    )


def render_markdown_report(config: ExperimentConfig, result: ExperimentResult) -> str:
    comparison = result.comparison
    lines = [
        f"# Experiment {config.experiment_id}\n",
        "\n",
        f"- Mode: {config.mode}\n",
        f"- Providers: {', '.join(config.providers)}\n",
        f"- Request ID: {result.request_id}\n",
        f"- Started: {result.started_at}\n",
        f"- Ended: {result.ended_at}\n",
        "\n",
        "## Results\n",
    ]
    for item in result.all_results:
        lines.extend(
            [
                f"### {item.provider}\n",
                f"- Model: {item.model}\n",
                f"- Latency: {item.latency_ms} ms\n",
                f"- Error: {item.error or 'none'}\n",
                "\n",
                "```\n",
                f"{item.text}\n",
                "```\n",
                "\n",
            ]
        )
    if comparison:
        lines.extend(
            [
                "## Comparison\n",
                f"- Stability score: {comparison.stability_score:.2f}\n",
                f"- Latency delta: {comparison.latency_delta_ms} ms\n",
                f"- Diff summary: {comparison.diff_summary}\n",
                "\n",
                "```json\n",
                json.dumps(comparison.tool_call_diff, indent=2),
                """
                "\n```
",
                """,
            ]
        )
    return "".join(lines)


def _build_request_id(experiment_id: str) -> str:
    return f"exp_{experiment_id}_{uuid4().hex[:8]}"


def _stable_seed(value: str) -> int:
    return sum(ord(ch) for ch in value) % 10000


def _require_providers(providers: list[str], count: int) -> list[str]:
    if len(providers) == 1 and count == 2:
        return providers * 2
    if len(providers) < count:
        raise ValueError(f"Expected at least {count} providers")
    return providers


def _build_comparison(
    primary: ExperimentProviderResult,
    secondary: ExperimentProviderResult | None,
) -> ExperimentComparison | None:
    if secondary is None:
        return None
    text_diff = compare_text(primary.text, secondary.text)
    tool_diff = compare_tool_calls(primary.tool_calls, secondary.tool_calls)
    latency_delta = secondary.latency_ms - primary.latency_ms
    return ExperimentComparison(
        stability_score=text_diff.score,
        latency_delta_ms=latency_delta,
        diff_summary=text_diff.summary,
        tool_call_diff=tool_diff,
    )


_unused_model_request = ModelRequest
_unused_any = Any
_unused_experiment_mode = ExperimentMode
