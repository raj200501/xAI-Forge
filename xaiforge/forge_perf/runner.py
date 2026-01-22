from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from xaiforge.forge_gateway import GatewayConfig, ModelGateway
from xaiforge.forge_gateway.models import ModelMessage, ModelRequest
from xaiforge.forge_perf.metrics import PerfMetrics, summarize_metrics


@dataclass(frozen=True)
class BenchResult:
    run_id: str
    started_at: str
    ended_at: str
    suite: str
    metrics: PerfMetrics
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "suite": self.suite,
            "metrics": self.metrics.to_dict(),
            "summary": self.summary,
        }


def run_bench(
    suite: str = "quick",
    provider: str = "mock",
    max_concurrency: int = 4,
    timeout_s: float = 30.0,
) -> BenchResult:
    run_id = f"bench_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    started_at = datetime.now(UTC).isoformat()
    tasks = _bench_tasks(suite)
    metrics = asyncio.run(_run_tasks(tasks, provider, max_concurrency, timeout_s))
    summary = summarize_metrics(metrics)
    ended_at = datetime.now(UTC).isoformat()
    result = BenchResult(
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        suite=suite,
        metrics=metrics,
        summary=summary,
    )
    _write_bench_reports(result)
    return result


async def _run_tasks(
    tasks: list[str],
    provider: str,
    max_concurrency: int,
    timeout_s: float,
) -> PerfMetrics:
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    latencies: list[int] = []
    errors = 0

    async def _run_task(task: str) -> None:
        nonlocal errors
        async with semaphore:
            request = ModelRequest(messages=[ModelMessage(role="user", content=task)], request_id=_request_id())
            config = GatewayConfig()
            config.provider = provider
            config.timeout_s = timeout_s
            gateway = ModelGateway(config=config)
            started = time.perf_counter()
            try:
                await gateway.generate(request)
                latency_ms = int((time.perf_counter() - started) * 1000)
                latencies.append(latency_ms)
            except Exception:
                errors += 1

    tasks_pending = [asyncio.create_task(_run_task(task)) for task in tasks]
    await asyncio.gather(*tasks_pending)
    return PerfMetrics(latencies_ms=latencies, errors=errors, total=len(tasks))


def _bench_tasks(suite: str) -> list[str]:
    if suite == "quick":
        return [
            "Summarize the release notes",
            "Compute 17*23",
            "List three safety guidelines",
            "Explain fallback routing",
        ]
    return [
        "Draft a short uptime update",
        "Compute 128/7",
        "Summarize the policy",
        "List two observability signals",
        "Explain canary traffic",
        "Compute 4^6",
    ]


def _write_bench_reports(result: BenchResult) -> None:
    reports_dir = Path("reports") / "perf"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"{result.run_id}.json"
    json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    md_path = reports_dir / f"{result.run_id}.md"
    md_path.write_text(_render_markdown(result), encoding="utf-8")


def _render_markdown(result: BenchResult) -> str:
    summary = result.summary
    lines = [
        f"# Perf Bench {result.run_id}\n",
        "\n",
        f"- Suite: {result.suite}\n",
        f"- Started: {result.started_at}\n",
        f"- Ended: {result.ended_at}\n",
        "\n",
        "## Summary\n",
        f"- p50 latency: {summary['p50_ms']} ms\n",
        f"- p90 latency: {summary['p90_ms']} ms\n",
        f"- p95 latency: {summary['p95_ms']} ms\n",
        f"- Avg latency: {summary['avg_ms']} ms\n",
        f"- Throughput: {summary['throughput_rps']} rps\n",
        f"- Error rate: {summary['error_rate']:.2%}\n",
    ]
    return "".join(lines)


def _request_id() -> str:
    return f"perf_{uuid4().hex[:10]}"
