from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import json
from pathlib import Path

import pytest

from xaiforge.forge_experiments.models import ExperimentConfig, ExperimentRequestTemplate
from xaiforge.forge_experiments.runner import run_experiment, save_experiment_artifacts
from xaiforge.forge_gateway.models import ModelMessage


@pytest.fixture()
def request_template() -> ExperimentRequestTemplate:
    return ExperimentRequestTemplate(messages=[ModelMessage(role="user", content="test")])


def test_experiment_ab(request_template: ExperimentRequestTemplate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.create(
        experiment_id="exp_ab",
        mode="ab",
        providers=["mock", "mock"],
        request_template=request_template,
    )
    result = run_experiment(config)
    assert result.primary.provider == "mock"
    assert result.comparison is not None
    assert result.comparison.stability_score >= 0.9


def test_experiment_shadow(request_template: ExperimentRequestTemplate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.create(
        experiment_id="exp_shadow",
        mode="shadow",
        providers=["mock", "mock"],
        request_template=request_template,
    )
    result = run_experiment(config)
    assert result.secondary is not None
    assert result.comparison is not None


def test_experiment_canary(request_template: ExperimentRequestTemplate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.create(
        experiment_id="exp_canary",
        mode="canary",
        providers=["mock", "mock"],
        request_template=request_template,
        traffic_split=1.0,
    )
    result = run_experiment(config)
    assert result.secondary is not None


def test_experiment_fallback(request_template: ExperimentRequestTemplate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.create(
        experiment_id="exp_fallback",
        mode="fallback",
        providers=["fail-mock", "mock"],
        request_template=request_template,
    )
    result = run_experiment(config)
    assert result.primary.provider == "mock"
    assert result.errors


def test_experiment_report_determinism(
    request_template: ExperimentRequestTemplate,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.create(
        experiment_id="exp_report",
        mode="ab",
        providers=["mock", "mock"],
        request_template=request_template,
    )
    result = run_experiment(config)
    manifest = save_experiment_artifacts(config, result, base_dir=tmp_path / ".xaiforge")
    report_path = Path(manifest.report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["experiment_id"] == "exp_report"
    assert payload["mode"] == "ab"
