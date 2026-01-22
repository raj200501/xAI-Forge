from __future__ import annotations

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
class LoadResult:
    run_id: str
    started_at: str
    ended_at: str
    duration_s: int
    concurrency: int
    request_rate: float
    metrics: PerfMetrics
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": self.duration_s,
            "concurrency": self.concurrency,
            "request_rate": self.request_rate,
            "metrics": self.metrics.to_dict(),
            "summary": self.summary,
        }


def run_load(
    duration_s: int = 10,
    concurrency: int = 10,
    ramp_up_s: int = 0,
    request_rate: float = 5.0,
    provider: str = "mock",
    timeout_s: float = 30.0,
) -> LoadResult:
    run_id = f"load_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    started_at = datetime.now(UTC).isoformat()
    metrics = asyncio.run(
        _run_load(duration_s, concurrency, ramp_up_s, request_rate, provider, timeout_s)
    )
    summary = summarize_metrics(metrics)
    ended_at = datetime.now(UTC).isoformat()
    result = LoadResult(
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_s=duration_s,
        concurrency=concurrency,
        request_rate=request_rate,
        metrics=metrics,
        summary=summary,
    )
    _write_load_reports(result)
    return result


async def _run_load(
    duration_s: int,
    concurrency: int,
    ramp_up_s: int,
    request_rate: float,
    provider: str,
    timeout_s: float,
) -> PerfMetrics:
    semaphore = asyncio.Semaphore(max(1, concurrency))
    latencies: list[int] = []
    errors = 0
    stop_at = time.perf_counter() + duration_s

    async def _worker(worker_id: int) -> None:
        nonlocal errors
        await asyncio.sleep((ramp_up_s / max(concurrency, 1)) * worker_id)
        while time.perf_counter() < stop_at:
            async with semaphore:
                request = ModelRequest(
                    messages=[ModelMessage(role="user", content=f"load ping {worker_id}")],
                    request_id=_request_id(),
                )
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
            await asyncio.sleep(max(0.0, 1.0 / max(request_rate, 0.1)))

    workers = [asyncio.create_task(_worker(index)) for index in range(concurrency)]
    await asyncio.gather(*workers)
    total = len(latencies) + errors
    return PerfMetrics(latencies_ms=latencies, errors=errors, total=total)


def _write_load_reports(result: LoadResult) -> None:
    reports_dir = Path("reports") / "perf"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"{result.run_id}.json"
    json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    md_path = reports_dir / f"{result.run_id}.md"
    md_path.write_text(_render_markdown(result), encoding="utf-8")


def _render_markdown(result: LoadResult) -> str:
    summary = result.summary
    lines = [
        f"# Perf Load {result.run_id}\n",
        "\n",
        f"- Duration: {result.duration_s} s\n",
        f"- Concurrency: {result.concurrency}\n",
        f"- Request rate: {result.request_rate} rps\n",
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
    return f"load_{uuid4().hex[:10]}"
