from __future__ import annotations

import json
from pathlib import Path

from xaiforge.benchmarks.report import BenchReport, build_bench_report, write_bench_report


def _sample_manifest(trace_id: str = "123") -> dict:
    return {
        "trace_id": trace_id,
        "task": "demo",
        "provider": "heuristic",
        "duration_s": 0.5,
    }


def _sample_events() -> list[dict]:
    return [
        {"type": "plan", "steps": ["Step one", "Step two"]},
        {"type": "tool_call", "tool_name": "calc", "arguments": {"expression": "2+2"}},
        {"type": "tool_result", "tool_name": "calc", "result": {"value": "4"}},
        {"type": "run_end", "status": "ok", "summary": "done"},
    ]


def test_build_bench_report() -> None:
    report = build_bench_report(_sample_manifest(), _sample_events())
    assert report.trace_id == "123"
    assert report.plan == ["Step one", "Step two"]
    assert report.tool_calls == 1
    assert report.errors == 0
    assert report.status == "ok"


def test_bench_report_markdown() -> None:
    report = BenchReport(
        trace_id="abc",
        task="demo",
        provider="heuristic",
        status="ok",
        tool_calls=2,
        errors=0,
        duration_s=1.2,
        summary="finished",
        plan=["a", "b"],
    )
    markdown = report.to_markdown()
    assert "# Bench Report: abc" in markdown
    assert "1. a" in markdown


def test_write_bench_report(tmp_path: Path) -> None:
    base_dir = tmp_path / ".xaiforge"
    report_path = write_bench_report(base_dir, _sample_manifest("999"), _sample_events())
    assert report_path.exists()
    latest_path = base_dir / "bench" / "latest.md"
    assert latest_path.exists()
    json_path = base_dir / "bench" / "999.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["trace_id"] == "999"
