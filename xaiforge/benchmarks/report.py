from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchReport:
    trace_id: str
    task: str
    provider: str
    status: str
    tool_calls: int
    errors: int
    duration_s: float | None
    summary: str
    plan: list[str]

    def to_markdown(self) -> str:
        lines = [
            f"# Bench Report: {self.trace_id}",
            "",
            "## Overview",
            f"- Task: {self.task}",
            f"- Provider: {self.provider}",
            f"- Status: {self.status}",
            f"- Tool calls: {self.tool_calls}",
            f"- Errors: {self.errors}",
            f"- Duration (s): {self.duration_s}",
            "",
            "## Plan",
        ]
        if self.plan:
            for idx, step in enumerate(self.plan, start=1):
                lines.append(f"{idx}. {step}")
        else:
            lines.append("No plan steps recorded.")
        lines.extend(["", "## Summary", self.summary, ""])
        return "\n".join(lines)


def build_bench_report(manifest: dict[str, Any], events: list[dict[str, Any]]) -> BenchReport:
    plan_steps: list[str] = []
    summary = ""
    status = ""
    tool_calls = 0
    errors = 0
    for event in events:
        event_type = event.get("type")
        if event_type == "plan":
            plan_steps = list(event.get("steps", []))
        if event_type == "tool_call":
            tool_calls += 1
        if event_type == "tool_error":
            errors += 1
        if event_type == "run_end":
            summary = event.get("summary", "")
            status = event.get("status", "")
    return BenchReport(
        trace_id=manifest.get("trace_id", ""),
        task=manifest.get("task", ""),
        provider=manifest.get("provider", ""),
        status=status,
        tool_calls=tool_calls,
        errors=errors,
        duration_s=manifest.get("duration_s"),
        summary=summary,
        plan=plan_steps,
    )


def write_bench_report(
    base_dir: Path, manifest: dict[str, Any], events: list[dict[str, Any]]
) -> Path:
    report = build_bench_report(manifest, events)
    bench_dir = base_dir / "bench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    report_path = bench_dir / f"{report.trace_id}.md"
    report_path.write_text(report.to_markdown(), encoding="utf-8")
    latest_path = bench_dir / "latest.md"
    latest_path.write_text(report.to_markdown(), encoding="utf-8")
    json_path = bench_dir / f"{report.trace_id}.json"
    json_payload = {
        "trace_id": report.trace_id,
        "task": report.task,
        "provider": report.provider,
        "status": report.status,
        "tool_calls": report.tool_calls,
        "errors": report.errors,
        "duration_s": report.duration_s,
        "summary": report.summary,
        "plan": report.plan,
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    return report_path
