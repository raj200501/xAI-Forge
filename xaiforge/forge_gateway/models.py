from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ModelMessage:
    role: Role
    content: str
    name: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class ModelRequest:
    messages: list[ModelMessage]
    tools: list[ToolDefinition] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 512
    seed: int | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "messages": [message.__dict__ for message in self.messages],
            "tools": [tool.__dict__ for tool in self.tools],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
            "stop": self.stop,
            "metadata": self.metadata,
            "request_id": self.request_id,
        }


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class UsageInfo:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ModelResponse:
    text: str
    tool_calls: list[ToolCall]
    usage: UsageInfo
    latency_ms: int
    provider: str
    model: str
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_stream_chunk(self) -> StreamChunk:
        return StreamChunk(
            index=0,
            text=self.text,
            is_final=True,
            tool_calls=self.tool_calls,
            usage=self.usage,
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "text": self.text,
                "tool_calls": [call.__dict__ for call in self.tool_calls],
                "usage": self.usage.__dict__,
                "latency_ms": self.latency_ms,
                "provider": self.provider,
                "model": self.model,
                "request_id": self.request_id,
                "metadata": self.metadata,
            },
            indent=2,
        )


@dataclass(frozen=True)
class StreamChunk:
    index: int
    text: str
    is_final: bool = False
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: UsageInfo | None = None


@dataclass(frozen=True)
class StreamEvent:
    request_id: str | None
    provider: str
    model: str
    chunk: StreamChunk


@dataclass
class BatchResult:
    responses: list[ModelResponse]
    failures: list[Exception]


class StreamIterable(Iterable[StreamEvent]):
    def __iter__(self) -> Iterable[StreamEvent]:
        raise NotImplementedError
