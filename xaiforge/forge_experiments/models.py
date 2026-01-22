from __future__ import annotations

# ruff: noqa: UP037
# ruff: noqa: I001

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from xaiforge.forge_gateway.models import ModelMessage, ModelRequest, ToolDefinition

ExperimentMode = Literal["shadow", "ab", "canary", "fallback"]


@dataclass(frozen=True)
class ExperimentRequestTemplate:
    messages: list[ModelMessage]
    tools: list[ToolDefinition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.2
    max_tokens: int = 512
    seed: int | None = 42
    stop: list[str] | None = None

    def to_request(self, request_id: str | None = None) -> ModelRequest:
        metadata = {**self.metadata}
        if self.tags:
            metadata.setdefault("tags", list(self.tags))
        return ModelRequest(
            messages=self.messages,
            tools=self.tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            seed=self.seed,
            stop=self.stop,
            metadata=metadata,
            request_id=request_id,
        )


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    created_at: str
    mode: ExperimentMode
    providers: list[str]
    traffic_split: float = 0.5
    max_concurrency: int = 4
    timeout_s: float = 30.0
    request_template: ExperimentRequestTemplate | None = None
    thresholds: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        experiment_id: str,
        mode: ExperimentMode,
        providers: list[str],
        request_template: ExperimentRequestTemplate | None,
        traffic_split: float = 0.5,
        max_concurrency: int = 4,
        timeout_s: float = 30.0,
        thresholds: dict[str, float] | None = None,
        tags: list[str] | None = None,
    ) -> "ExperimentConfig":
        return cls(
            experiment_id=experiment_id,
            created_at=datetime.now(UTC).isoformat(),
            mode=mode,
            providers=providers,
            traffic_split=traffic_split,
            max_concurrency=max_concurrency,
            timeout_s=timeout_s,
            request_template=request_template,
            thresholds=thresholds or {},
            tags=tags or [],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "providers": list(self.providers),
            "traffic_split": self.traffic_split,
            "max_concurrency": self.max_concurrency,
            "timeout_s": self.timeout_s,
            "request_template": self._template_dict(),
            "thresholds": self.thresholds,
            "tags": self.tags,
        }

    def _template_dict(self) -> dict[str, Any] | None:
        if not self.request_template:
            return None
        return {
            "messages": [message.__dict__ for message in self.request_template.messages],
            "tools": [tool.__dict__ for tool in self.request_template.tools],
            "tags": list(self.request_template.tags),
            "metadata": self.request_template.metadata,
            "temperature": self.request_template.temperature,
            "max_tokens": self.request_template.max_tokens,
            "seed": self.request_template.seed,
            "stop": self.request_template.stop,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExperimentConfig":
        template = payload.get("request_template")
        request_template = None
        if template:
            request_template = ExperimentRequestTemplate(
                messages=[ModelMessage(**message) for message in template.get("messages", [])],
                tools=[ToolDefinition(**tool) for tool in template.get("tools", [])],
                tags=template.get("tags", []),
                metadata=template.get("metadata", {}),
                temperature=template.get("temperature", 0.2),
                max_tokens=template.get("max_tokens", 512),
                seed=template.get("seed"),
                stop=template.get("stop"),
            )
        return cls(
            experiment_id=payload["experiment_id"],
            created_at=payload["created_at"],
            mode=payload["mode"],
            providers=payload.get("providers", []),
            traffic_split=payload.get("traffic_split", 0.5),
            max_concurrency=payload.get("max_concurrency", 4),
            timeout_s=payload.get("timeout_s", 30.0),
            request_template=request_template,
            thresholds=payload.get("thresholds", {}),
            tags=payload.get("tags", []),
        )


@dataclass(frozen=True)
class ExperimentProviderResult:
    provider: str
    model: str
    text: str
    tool_calls: list[dict[str, Any]]
    latency_ms: int
    usage: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class ExperimentComparison:
    stability_score: float
    latency_delta_ms: int
    diff_summary: str
    tool_call_diff: dict[str, Any]


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    mode: ExperimentMode
    request_id: str
    primary: ExperimentProviderResult
    secondary: ExperimentProviderResult | None
    all_results: list[ExperimentProviderResult]
    comparison: ExperimentComparison | None
    errors: list[str]
    started_at: str
    ended_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "mode": self.mode,
            "request_id": self.request_id,
            "primary": _provider_to_dict(self.primary),
            "secondary": _provider_to_dict(self.secondary) if self.secondary else None,
            "all_results": [_provider_to_dict(item) for item in self.all_results],
            "comparison": _comparison_to_dict(self.comparison),
            "errors": list(self.errors),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass(frozen=True)
class ExperimentRunSummary:
    experiment_id: str
    created_at: str
    mode: ExperimentMode
    providers: list[str]
    request_id: str
    status: str
    stability_score: float | None
    latency_delta_ms: int | None
    error_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "created_at": self.created_at,
            "mode": self.mode,
            "providers": self.providers,
            "request_id": self.request_id,
            "status": self.status,
            "stability_score": self.stability_score,
            "latency_delta_ms": self.latency_delta_ms,
            "error_rate": self.error_rate,
        }


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    created_at: str
    report_path: str
    config_path: str
    summary: ExperimentRunSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "created_at": self.created_at,
            "report_path": self.report_path,
            "config_path": self.config_path,
            "summary": self.summary.to_dict(),
        }


def _provider_to_dict(result: ExperimentProviderResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "provider": result.provider,
        "model": result.model,
        "text": result.text,
        "tool_calls": result.tool_calls,
        "latency_ms": result.latency_ms,
        "usage": result.usage,
        "error": result.error,
    }


def _comparison_to_dict(comparison: ExperimentComparison | None) -> dict[str, Any] | None:
    if comparison is None:
        return None
    return {
        "stability_score": comparison.stability_score,
        "latency_delta_ms": comparison.latency_delta_ms,
        "diff_summary": comparison.diff_summary,
        "tool_call_diff": comparison.tool_call_diff,
    }


def serialize_experiment_result(result: ExperimentResult) -> str:
    return json.dumps(result.to_dict(), indent=2)
