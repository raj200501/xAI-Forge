from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator

import httpx

from xaiforge.forge_gateway.models import (
    ModelRequest,
    ModelResponse,
    StreamChunk,
    StreamEvent,
    ToolCall,
    UsageInfo,
)
from xaiforge.forge_gateway.providers.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.name = "openai-compat"
        self.model = os.getenv("XAIFORGE_GATEWAY_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.getenv("XAIFORGE_GATEWAY_BASE_URL", "")
        self.api_key = api_key or os.getenv("XAIFORGE_GATEWAY_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not self.base_url:
            raise ValueError("OpenAI-compatible base URL is not configured")
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            payload["tools"] = [
                {"type": "function", "function": tool.__dict__} for tool in request.tools
            ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        text = message.get("content") or ""
        tool_calls: list[ToolCall] = []
        for call in message.get("tool_calls", []) or []:
            tool_calls.append(
                ToolCall(
                    name=call["function"]["name"], arguments=call["function"].get("arguments", {})
                )
            )
        usage_data = data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
            completion_tokens=int(usage_data.get("completion_tokens", 0)),
            total_tokens=int(usage_data.get("total_tokens", 0)),
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
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        if not self.base_url:
            raise ValueError("OpenAI-compatible base URL is not configured")
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        async with (
            httpx.AsyncClient(timeout=30.0) as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload_line = line[len("data:") :].strip()
                if payload_line == "[DONE]":
                    break
                chunk_data = httpx.Response(200, content=payload_line).json()
                delta = chunk_data["choices"][0]["delta"]
                text = delta.get("content", "")
                if text:
                    yield StreamEvent(
                        request_id=request.request_id,
                        provider=self.name,
                        model=self.model,
                        chunk=StreamChunk(index=0, text=text),
                    )
