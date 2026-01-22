from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from xaiforge.forge_gateway.batching import BatchScheduler
from xaiforge.forge_gateway.config import GatewayConfig
from xaiforge.forge_gateway.models import ModelRequest, ModelResponse, StreamEvent
from xaiforge.forge_gateway.providers import (
    LocalHTTPProvider,
    MockProvider,
    OpenAICompatibleProvider,
)
from xaiforge.forge_gateway.providers.base import ModelProvider
from xaiforge.forge_gateway.reliability import CircuitBreaker
from xaiforge.forge_safety.policy import SafetyPolicy
from xaiforge.forge_safety.redaction import redact_payload


@dataclass
class GatewayResult:
    response: ModelResponse
    attempts: int
    latency_ms: int


class ModelGateway:
    def __init__(
        self,
        config: GatewayConfig | None = None,
        provider: ModelProvider | None = None,
        trace_hook: Callable[[dict[str, Any]], None] | None = None,
        safety_policy: SafetyPolicy | None = None,
    ) -> None:
        self.config = config or GatewayConfig()
        self.trace_hook = trace_hook
        self.safety_policy = safety_policy
        self.provider = provider or self._resolve_provider()
        self._breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_failures,
            reset_timeout_s=self.config.circuit_reset_s,
        )
        self._batcher: BatchScheduler | None = None
        if self.config.batch.enabled:
            self._batcher = BatchScheduler(self.provider.generate_batch, self.config.batch)

    def _resolve_provider(self) -> ModelProvider:
        if self.config.provider == "openai-compat":
            return OpenAICompatibleProvider()
        if self.config.provider == "local-http":
            return LocalHTTPProvider()
        return MockProvider()

    def _emit_trace(self, payload: dict[str, Any]) -> None:
        if self.trace_hook:
            self.trace_hook(payload)

    async def _invoke(self, request: ModelRequest) -> ModelResponse:
        if self.config.circuit_breaker and not self._breaker.allow():
            raise RuntimeError("Circuit breaker open")
        start = time.perf_counter()
        response = await asyncio.wait_for(
            self.provider.generate(request), timeout=self.config.timeout_s
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._emit_trace(
            {
                "type": "gateway_response",
                "provider": response.provider,
                "model": response.model,
                "latency_ms": latency_ms,
                "request_id": request.request_id,
            }
        )
        if self.config.circuit_breaker:
            self._breaker.record_success()
        return response

    async def generate(self, request: ModelRequest) -> GatewayResult:
        if self.safety_policy and self.config.safety_enabled:
            redacted = redact_payload(request.to_payload())
            self.safety_policy.evaluate(redacted["payload"])
        attempts = 0
        start = time.perf_counter()
        policy = self.config.retry
        while True:
            attempts += 1
            try:
                if self._batcher:
                    self._batcher.start()
                    response = await self._batcher.submit(request)
                else:
                    response = await self._invoke(request)
                break
            except Exception:
                if self.config.circuit_breaker:
                    self._breaker.record_failure()
                if attempts >= policy.max_attempts:
                    raise
                await asyncio.sleep(policy.backoff(attempts))
        latency_ms = int((time.perf_counter() - start) * 1000)
        return GatewayResult(response=response, attempts=attempts, latency_ms=latency_ms)

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        if self.safety_policy and self.config.safety_enabled:
            redacted = redact_payload(request.to_payload())
            self.safety_policy.evaluate(redacted["payload"])
        async for event in self.provider.stream(request):
            yield event


async def build_gateway(config: GatewayConfig | None = None) -> ModelGateway:
    return ModelGateway(config=config)
