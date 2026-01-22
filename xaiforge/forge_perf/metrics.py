from __future__ import annotations

# ruff: noqa: UP035
# ruff: noqa: I001
# ruff: noqa: F811

from dataclasses import dataclass
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class PerfMetrics:
    latencies_ms: list[int]
    errors: int
    total: int
    ttft_ms: list[int] | None = None

    def to_dict(self) -> dict:
        return {
            "latencies_ms": self.latencies_ms,
            "errors": self.errors,
            "total": self.total,
            "ttft_ms": self.ttft_ms or [],
        }


def summarize_metrics(metrics: PerfMetrics) -> dict:
    latencies = sorted(metrics.latencies_ms)
    return {
        "p50_ms": _percentile(latencies, 0.5),
        "p90_ms": _percentile(latencies, 0.9),
        "p95_ms": _percentile(latencies, 0.95),
        "avg_ms": int(mean(latencies)) if latencies else 0,
        "throughput_rps": _throughput(metrics),
        "error_rate": (metrics.errors / metrics.total) if metrics.total else 0.0,
        "ttft_p50_ms": _percentile(sorted(metrics.ttft_ms or []), 0.5),
    }


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    index = int(round((len(values) - 1) * pct))
    return values[min(max(index, 0), len(values) - 1)]


def _throughput(metrics: PerfMetrics) -> float:
    if not metrics.latencies_ms:
        return 0.0
    total_time_s = sum(metrics.latencies_ms) / 1000.0
    if total_time_s == 0:
        return 0.0
    return round(metrics.total / total_time_s, 3)


def combine_metrics(metrics_list: Iterable[PerfMetrics]) -> PerfMetrics:
    latencies: list[int] = []
    errors = 0
    total = 0
    ttft: list[int] = []
    for metrics in metrics_list:
        latencies.extend(metrics.latencies_ms)
        errors += metrics.errors
        total += metrics.total
        if metrics.ttft_ms:
            ttft.extend(metrics.ttft_ms)
    return PerfMetrics(latencies_ms=latencies, errors=errors, total=total, ttft_ms=ttft)


def summarize_metrics(metrics: PerfMetrics) -> dict:
    latencies = sorted(metrics.latencies_ms)
    return {
        "p50_ms": _percentile_floor(latencies, 0.5),
        "p90_ms": _percentile_floor(latencies, 0.9),
        "p95_ms": _percentile_floor(latencies, 0.95),
        "avg_ms": int(mean(latencies)) if latencies else 0,
        "throughput_rps": _throughput(metrics),
        "error_rate": (metrics.errors / metrics.total) if metrics.total else 0.0,
        "ttft_p50_ms": _percentile_floor(sorted(metrics.ttft_ms or []), 0.5),
    }


def _percentile_floor(values: list[int], pct: float) -> int:
    if not values:
        return 0
    index = int((len(values) - 1) * pct)
    return values[min(max(index, 0), len(values) - 1)]
