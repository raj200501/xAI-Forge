from __future__ import annotations

import os
import time

import httpx

from xaiforge.forge_gateway.models import ModelRequest, ModelResponse, ToolCall, UsageInfo
from xaiforge.forge_gateway.providers.base import ModelProvider


class LocalHTTPProvider(ModelProvider):
    def __init__(self, endpoint: str | None = None) -> None:
        self.name = "local-http"
        self.model = os.getenv("XAIFORGE_GATEWAY_MODEL", "local")
        self.endpoint = endpoint or os.getenv("XAIFORGE_LOCAL_HTTP", "http://127.0.0.1:11434")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.endpoint}/v1/chat/completions", json=payload)
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
