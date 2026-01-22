from __future__ import annotations

from pathlib import Path

import pytest

from xaiforge.forge_perf.gate import gate_performance
from xaiforge.forge_perf.load import run_load
from xaiforge.forge_perf.metrics import PerfMetrics, summarize_metrics
from xaiforge.forge_perf.runner import run_bench


def test_perf_metrics_summary() -> None:
    metrics = PerfMetrics(latencies_ms=[100, 200, 300, 400], errors=1, total=5)
    summary = summarize_metrics(metrics)
    assert summary["p50_ms"] == 200
    assert summary["p90_ms"] >= summary["p50_ms"]
    assert summary["error_rate"] == 0.2


def test_perf_gate(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text('{"p90_ms": 300, "throughput_rps": 2.0}', encoding="utf-8")
    metrics = PerfMetrics(latencies_ms=[100, 120, 130, 140], errors=0, total=4)
    result = gate_performance(metrics, baseline_path)
    assert "summary" in result


def test_perf_bench_quick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_bench(suite="quick", provider="mock", max_concurrency=1, timeout_s=5.0)
    assert result.summary["p50_ms"] >= 0


def test_perf_load_mini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_load(duration_s=1, concurrency=1, request_rate=1.0, provider="mock", timeout_s=5.0)
    assert result.summary["error_rate"] >= 0.0
