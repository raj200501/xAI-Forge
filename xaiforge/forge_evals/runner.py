from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xaiforge.forge_evals.scorers import (
    exact_match,
    json_schema_match,
    regex_match,
    tool_call_match,
)
from xaiforge.forge_gateway.models import ModelMessage, ModelRequest, ToolDefinition
from xaiforge.forge_gateway.providers.mock import MockProvider


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    messages: list[ModelMessage]
    expected: Any
    rubric: str
    tags: list[str]
    difficulty: str


@dataclass(frozen=True)
class EvalScore:
    passed: bool
    reason: str


@dataclass
class EvalResult:
    case: EvalCase
    response_text: str
    score: EvalScore
    latency_ms: int


@dataclass
class EvalReport:
    dataset: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[EvalResult]
    created_at: float

    def to_json(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "created_at": self.created_at,
            "results": [
                {
                    "id": result.case.case_id,
                    "passed": result.score.passed,
                    "reason": result.score.reason,
                    "latency_ms": result.latency_ms,
                    "response": result.response_text,
                }
                for result in self.results
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Eval Report: {self.dataset}",
            "",
            f"- Total: {self.total}",
            f"- Passed: {self.passed}",
            f"- Failed: {self.failed}",
            f"- Pass rate: {self.pass_rate:.2%}",
            "",
            "| Case | Passed | Reason |",
            "| --- | --- | --- |",
        ]
        for result in self.results:
            lines.append(
                f"| {result.case.case_id} | {result.score.passed} | {result.score.reason} |"
            )
        return "\n".join(lines)


def load_dataset(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            messages = [ModelMessage(**message) for message in payload["messages"]]
            cases.append(
                EvalCase(
                    case_id=payload["id"],
                    messages=messages,
                    expected=payload["expected"],
                    rubric=payload["rubric"],
                    tags=payload.get("tags", []),
                    difficulty=payload.get("difficulty", "medium"),
                )
            )
    return cases


def _score_case(case: EvalCase, response_text: str) -> EvalScore:
    if case.rubric == "exact_match":
        result = exact_match(response_text, str(case.expected))
    elif case.rubric == "regex_match":
        result = regex_match(response_text, str(case.expected))
    elif case.rubric == "json_schema_match":
        result = json_schema_match(response_text, case.expected)
    elif case.rubric == "tool_call_match":
        result = tool_call_match(response_text, case.expected)
    else:
        result = EvalScore(passed=False, reason=f"unknown rubric {case.rubric}")
    return EvalScore(passed=result.passed, reason=result.reason)


def run_eval(
    dataset_path: Path,
    report_dir: Path,
    provider: MockProvider | None = None,
) -> EvalReport:
    cases = load_dataset(dataset_path)
    provider = provider or MockProvider()
    results: list[EvalResult] = []
    for case in cases:
        metadata: dict[str, Any] = {}
        if case.rubric in {"exact_match", "regex_match"}:
            metadata["expected_text"] = str(case.expected)
        if case.rubric == "json_schema_match":
            metadata["expected_text"] = json.dumps(case.expected)
        request = ModelRequest(messages=case.messages, metadata=metadata)
        if case.rubric == "tool_call_match":
            request = ModelRequest(
                messages=case.messages,
                tools=[ToolDefinition(name=case.expected["name"], description="", schema={})],
                metadata={"tool_call_override": case.expected},
            )
        start = time.perf_counter()
        response = provider.generate(request)
        if hasattr(response, "__await__"):
            response = asyncio.run(response)  # type: ignore[assignment]
        if hasattr(response, "__await__"):
            response = __import__("asyncio").run(response)  # type: ignore[assignment]
        latency_ms = int((time.perf_counter() - start) * 1000)
        response_text = response.text
        if case.rubric == "tool_call_match" and response.tool_calls:
            response_text = json.dumps(
                {
                    "name": response.tool_calls[0].name,
                    "arguments": response.tool_calls[0].arguments,
                }
            )
        score = _score_case(case, response_text)
        results.append(
            EvalResult(case=case, response_text=response_text, score=score, latency_ms=latency_ms)
        )
    passed = sum(1 for result in results if result.score.passed)
    failed = len(results) - passed
    report = EvalReport(
        dataset=dataset_path.stem,
        total=len(results),
        passed=passed,
        failed=failed,
        pass_rate=passed / max(len(results), 1),
        results=results,
        created_at=time.time(),
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{dataset_path.stem}.json"
    report_path.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    report_md = report_dir / f"{dataset_path.stem}.md"
    report_md.write_text(report.to_markdown(), encoding="utf-8")
    return report


def gate_report(report: EvalReport, baseline_path: Path, threshold: float = 0.95) -> None:
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    else:
        baseline = {"pass_rate": 0.0}
    baseline_rate = float(baseline.get("pass_rate", 0.0))
    if report.pass_rate < min(threshold, baseline_rate):
        raise ValueError(f"Eval gate failed: {report.pass_rate:.2%} < baseline {baseline_rate:.2%}")
