from pathlib import Path

from xaiforge.forge_evals.runner import gate_report, load_dataset, run_eval
from xaiforge.forge_gateway.providers.mock import MockProvider


def test_dataset_loads_cases():
    dataset = Path("xaiforge/forge_evals/datasets/trace_ops.jsonl")
    cases = load_dataset(dataset)
    assert len(cases) >= 30
    assert any(case.rubric == "tool_call_match" for case in cases)


def test_run_eval_and_gate(tmp_path):
    dataset = Path("xaiforge/forge_evals/datasets/trace_ops.jsonl")
    report = run_eval(dataset, tmp_path, provider=MockProvider())
    assert report.pass_rate >= 0.95
    baseline = Path("xaiforge/forge_evals/baseline.json")
    gate_report(report, baseline)
