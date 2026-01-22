from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass

from xaiforge.forge_gateway.models import BatchResult, ModelRequest, ModelResponse

BatchHandler = Callable[[list[ModelRequest]], Awaitable[list[ModelResponse]]]


@dataclass
class BatchConfig:
    enabled: bool = False
    max_batch_size: int = 4
    max_wait_ms: int = 25


class BatchScheduler:
    def __init__(self, handler: BatchHandler, config: BatchConfig) -> None:
        self._handler = handler
        self._config = config
        self._queue: asyncio.Queue[tuple[ModelRequest, asyncio.Future[ModelResponse]]] = (
            asyncio.Queue()
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def submit(self, request: ModelRequest) -> ModelResponse:
        future: asyncio.Future[ModelResponse] = asyncio.Future()
        await self._queue.put((request, future))
        return await future

    async def _worker(self) -> None:
        while True:
            request, future = await self._queue.get()
            batch = [(request, future)]
            if self._config.max_wait_ms > 0:
                try:
                    await asyncio.sleep(self._config.max_wait_ms / 1000)
                except asyncio.CancelledError:
                    break
            while not self._queue.empty() and len(batch) < self._config.max_batch_size:
                batch.append(self._queue.get_nowait())
            requests = [item[0] for item in batch]
            try:
                responses = await self._handler(requests)
            except Exception as exc:
                for _, fut in batch:
                    if not fut.done():
                        fut.set_exception(exc)
                continue
            for response, (_, fut) in zip(responses, batch, strict=False):
                if not fut.done():
                    fut.set_result(response)


async def run_batch(handler: BatchHandler, requests: list[ModelRequest]) -> BatchResult:
    failures: list[Exception] = []
    responses: list[ModelResponse] = []
    try:
        responses = await handler(requests)
    except Exception as exc:
        failures.append(exc)
    return BatchResult(responses=responses, failures=failures)
