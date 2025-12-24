from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from xaiforge.agent.runner import PROVIDERS, replay_trace, stream_run
from xaiforge.events import event_schema
from xaiforge.tools.registry import build_registry
from xaiforge.trace_store import TraceReader, list_manifests


app = FastAPI(title="xAI-Forge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    task: str
    root: str = "."
    provider: str = "heuristic"
    allow_net: bool = False
    plugins: list[str] = []


@app.get("/api/traces")
async def api_traces() -> list[dict]:
    return list_manifests(Path(".xaiforge"))


@app.get("/api/tools")
async def api_tools() -> list[dict]:
    registry = build_registry()
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        }
        for spec in registry.specs()
    ]


@app.get("/api/providers")
async def api_providers() -> list[str]:
    return list(PROVIDERS.keys())


@app.get("/api/schema/events")
async def api_event_schema() -> dict:
    return event_schema()


@app.get("/api/traces/{trace_id}")
async def api_trace(trace_id: str) -> dict:
    reader = TraceReader(Path(".xaiforge"), trace_id)
    try:
        return reader.load_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trace not found") from exc


@app.get("/api/traces/{trace_id}/events")
async def api_trace_events(trace_id: str) -> list[Dict]:
    reader = TraceReader(Path(".xaiforge"), trace_id)
    events = []
    for line in reader.iter_events():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


@app.post("/api/run")
async def api_run(request: RunRequest) -> EventSourceResponse:
    async def event_stream() -> AsyncIterator[dict]:
        queue: asyncio.Queue[str] = asyncio.Queue()

        def on_event(payload: str) -> None:
            queue.put_nowait(payload)

        async def runner() -> None:
            await stream_run(
                task=request.task,
                provider_name=request.provider,
                root=Path(request.root),
                allow_net=request.allow_net,
                on_event=on_event,
                plugins=request.plugins,
            )

        task = asyncio.create_task(runner())
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield {"event": "message", "data": payload}
                except asyncio.TimeoutError:
                    if task.done() and queue.empty():
                        break
        finally:
            await task

    return EventSourceResponse(event_stream())


@app.post("/api/replay/{trace_id}")
async def api_replay(trace_id: str) -> EventSourceResponse:
    async def event_stream() -> AsyncIterator[dict]:
        queue: asyncio.Queue[str] = asyncio.Queue()

        def on_event(payload: str) -> None:
            queue.put_nowait(payload)

        async def runner() -> None:
            await replay_trace(trace_id, on_event)

        task = asyncio.create_task(runner())
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield {"event": "message", "data": payload}
                except asyncio.TimeoutError:
                    if task.done() and queue.empty():
                        break
        finally:
            await task

    return EventSourceResponse(event_stream())
