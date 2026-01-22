from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from xaiforge.forge_gateway.models import (
    ModelRequest,
    ModelResponse,
    StreamChunk,
    StreamEvent,
    ToolCall,
    UsageInfo,
)
from xaiforge.forge_gateway.providers.base import ModelProvider


@dataclass
class MockProvider(ModelProvider):
    name: str = "mock"
    model: str = "mock-001"
    latency_ms: int = 12

    def _stable_text(self, request: ModelRequest) -> str:
        expected_override = request.metadata.get("expected_text")
        if isinstance(expected_override, str) and expected_override:
            return expected_override
        payload = json.dumps(request.to_payload(), sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        prompt = " ".join(message.content for message in request.messages)
        return f"MOCK[{digest}] {prompt}".strip()

    def _simulate_tool_calls(self, request: ModelRequest, text: str) -> list[ToolCall]:
        if not request.tools:
            return []
        override = request.metadata.get("tool_call_override")
        if isinstance(override, dict) and override.get("name"):
            return [
                ToolCall(
                    name=str(override["name"]),
                    arguments=dict(override.get("arguments", {})),
                )
            ]
        if request.metadata.get("force_tool_call"):
            tool = request.tools[0]
            return [ToolCall(name=tool.name, arguments={"input": text[:24]})]
        if "tool:" in text:
            tool = request.tools[0]
            return [ToolCall(name=tool.name, arguments={"input": text.split("tool:")[-1].strip()})]
        return []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.perf_counter()
        await asyncio.sleep(self.latency_ms / 1000)
        text = self._stable_text(request)
        tool_calls = self._simulate_tool_calls(request, text)
        usage = UsageInfo(
            prompt_tokens=max(
                1, len(" ".join(message.content for message in request.messages)) // 4
            ),
            completion_tokens=max(1, len(text) // 4),
            total_tokens=max(2, len(text) // 2),
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ModelResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=latency_ms,
            provider=self.name,
            model=self.model,
            request_id=request.request_id,
            metadata={"seed": request.seed},
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        start = time.perf_counter()
        text = self._stable_text(request)
        tool_calls = self._simulate_tool_calls(request, text)
        words = text.split()
        for index, word in enumerate(words):
            await asyncio.sleep(self.latency_ms / 1000)
            chunk = StreamChunk(index=index, text=word + " ")
            yield StreamEvent(
                request_id=request.request_id,
                provider=self.name,
                model=self.model,
                chunk=chunk,
            )
        _ = int((time.perf_counter() - start) * 1000)
        usage = UsageInfo(
            prompt_tokens=max(1, len(words) // 2),
            completion_tokens=len(words),
            total_tokens=len(words) * 2,
        )
        final_chunk = StreamChunk(
            index=len(words),
            text="",
            is_final=True,
            tool_calls=tool_calls,
            usage=usage,
        )
        yield StreamEvent(
            request_id=request.request_id,
            provider=self.name,
            model=self.model,
            chunk=final_chunk,
        )
