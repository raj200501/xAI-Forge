from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from xaiforge.forge_gateway.models import ModelRequest, ModelResponse, StreamEvent


class ModelProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        response = await self.generate(request)
        yield StreamEvent(
            request_id=response.request_id,
            provider=response.provider,
            model=response.model,
            chunk=response.to_stream_chunk(),
        )

    async def generate_batch(self, requests: list[ModelRequest]) -> list[ModelResponse]:
        responses: list[ModelResponse] = []
        for request in requests:
            responses.append(await self.generate(request))
        return responses
