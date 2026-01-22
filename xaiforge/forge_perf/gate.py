from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xaiforge.forge_perf.metrics import PerfMetrics, summarize_metrics


@dataclass(frozen=True)
class PerfGateError(Exception):
    message: str
    summary: dict[str, Any]

    def __str__(self) -> str:
        return self.message


def gate_performance(
    metrics: PerfMetrics,
    baseline_path: Path,
    max_latency_regression: float = 0.2,
    min_throughput_regression: float = 0.2,
) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    summary = summarize_metrics(metrics)
    regressions: list[str] = []
    if _regression(summary["p90_ms"], baseline["p90_ms"]) > max_latency_regression:
        regressions.append("p90 latency regression")
    if _regression(summary["throughput_rps"], baseline["throughput_rps"], inverse=True) > min_throughput_regression:
        regressions.append("throughput regression")
    if regressions:
        raise PerfGateError(
            "Performance regression detected: " + ", ".join(regressions),
            {"summary": summary, "baseline": baseline},
        )
    return {"summary": summary, "baseline": baseline}


def _regression(current: float, baseline: float, inverse: bool = False) -> float:
    if baseline == 0:
        return 0.0
    if inverse:
        return max((baseline - current) / baseline, 0.0)
    return max((current - baseline) / baseline, 0.0)
