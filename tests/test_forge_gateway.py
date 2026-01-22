import asyncio
from dataclasses import dataclass

import pytest

from xaiforge.forge_gateway.config import GatewayConfig
from xaiforge.forge_gateway.gateway import ModelGateway
from xaiforge.forge_gateway.models import ModelMessage, ModelRequest
from xaiforge.forge_gateway.providers.base import ModelProvider
from xaiforge.forge_gateway.providers.mock import MockProvider
from xaiforge.forge_gateway.reliability import RetryPolicy


@pytest.mark.asyncio
async def test_gateway_stream_orders_chunks():
    gateway = ModelGateway(config=GatewayConfig(), provider=MockProvider())
    request = ModelRequest(messages=[ModelMessage(role="user", content="streaming test")])
    chunks = []
    async for event in gateway.stream(request):
        chunks.append(event.chunk)
    assert chunks, "Expected chunks from stream"
    assert chunks[-1].is_final is True
    indices = [chunk.index for chunk in chunks]
    assert indices == sorted(indices)


@pytest.mark.asyncio
async def test_gateway_batching_coalesces_requests():
    config = GatewayConfig()
    config.batch.enabled = True
    config.batch.max_batch_size = 2
    gateway = ModelGateway(config=config, provider=MockProvider())
    request_a = ModelRequest(messages=[ModelMessage(role="user", content="batch A")])
    request_b = ModelRequest(messages=[ModelMessage(role="user", content="batch B")])
    result_a, result_b = await asyncio.gather(
        gateway.generate(request_a), gateway.generate(request_b)
    )
    assert result_a.response.provider == "mock"
    assert result_b.response.provider == "mock"


@dataclass
class FlakyProvider(ModelProvider):
    name: str = "flaky"
    model: str = "mock-001"
    failures: int = 0

    async def generate(self, request: ModelRequest):
        if self.failures < 1:
            self.failures += 1
            raise RuntimeError("temporary failure")
        return await MockProvider().generate(request)


@pytest.mark.asyncio
async def test_gateway_retries_on_failure():
    config = GatewayConfig(retry=RetryPolicy(max_attempts=2))
    provider = FlakyProvider()
    gateway = ModelGateway(config=config, provider=provider)
    result = await gateway.generate(
        ModelRequest(messages=[ModelMessage(role="user", content="retry")])
    )
    assert result.attempts == 2


@dataclass
class SlowProvider(ModelProvider):
    name: str = "slow"
    model: str = "mock-001"

    async def generate(self, request: ModelRequest):
        await asyncio.sleep(0.2)
        return await MockProvider().generate(request)


@pytest.mark.asyncio
async def test_gateway_timeout():
    config = GatewayConfig()
    config.timeout_s = 0.05
    gateway = ModelGateway(config=config, provider=SlowProvider())
    with pytest.raises(asyncio.TimeoutError):
        await gateway.generate(ModelRequest(messages=[ModelMessage(role="user", content="slow")]))
