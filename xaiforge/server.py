from __future__ import annotations

# fmt: off

# ruff: noqa: I001
# ruff: noqa: E501

import asyncio
import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from xaiforge.agent.runner import PROVIDERS, replay_trace, stream_run
from xaiforge.compat.fastapi import CORSMiddleware, FastAPI, HTTPException
from xaiforge.compat.pydantic import BaseModel
from xaiforge.compat.sse_starlette import EventSourceResponse
from xaiforge.events import event_schema
from xaiforge.observability.logging import LoggingConfig, configure_logging
from xaiforge.observability.otel import configure_otel
from xaiforge.tools.registry import build_registry
from xaiforge.trace_store import TraceReader, list_manifests
from xaiforge.forge_experiments.models import ExperimentConfig, ExperimentRequestTemplate
from xaiforge.forge_experiments.runner import run_experiment, save_experiment_artifacts, list_experiments
from xaiforge.forge_gateway import GatewayConfig, ModelGateway
from xaiforge.forge_gateway.models import ModelMessage, ToolDefinition, ModelRequest
from xaiforge.forge_index.builder import build_index, load_index_stats

app = FastAPI(title="xAI-Forge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if os.getenv("XAIFORGE_ENABLE_LOGGING") == "1":
    configure_logging(LoggingConfig.from_env())
if os.getenv("XAIFORGE_ENABLE_OTEL") == "1":
    configure_otel()
if os.getenv("XAIFORGE_ENABLE_HEALTH") == "1":

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "providers": list(PROVIDERS.keys()),
            "tools": len(build_registry().specs()),
        }


class RunRequest(BaseModel):
    task: str
    root: str = "."
    provider: str = "heuristic"
    allow_net: bool = False
    plugins: list[str] = []
    request_id: str | None = None


class ExperimentRunRequest(BaseModel):
    mode: str = "ab"
    providers: list[str] = ["mock"]
    task: str | None = None
    request_template: dict | None = None
    max_concurrency: int = 4
    timeout_s: float = 30.0


class GatewayRunRequest(BaseModel):
    provider: str = "mock"
    messages: list[dict] = []
    tools: list[dict] = []
    temperature: float = 0.2
    max_tokens: int = 512
    seed: int | None = None
    metadata: dict = {}
    request_id: str | None = None


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


@app.get("/api/plugins")
async def api_plugins() -> list[str]:
    from xaiforge.plugins.registry import available_plugins

    return available_plugins()


@app.get("/api/policy/summary")
async def api_policy_summary() -> dict:
    from xaiforge.policy.loader import load_policy_from_env
    from xaiforge.policy.cli import summarize_policy

    policy = load_policy_from_env()
    if not policy:
        return {"enabled": False}
    summary = summarize_policy(policy.config)
    summary_payload = summary.__dict__
    return {"enabled": True, "summary": summary_payload}
    return {"enabled": True, "summary": summary.to_dict()}


@app.get("/api/schema/events")
async def api_event_schema() -> dict:
    return event_schema()


@app.post("/api/gateway/run")
async def api_gateway_run(request: GatewayRunRequest) -> dict:
    messages = [ModelMessage(**message) for message in request.messages]
    tools = [ToolDefinition(**tool) for tool in request.tools]
    model_request = ModelRequest(
        messages=messages,
        tools=tools,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        seed=request.seed,
        metadata=request.metadata,
        request_id=request.request_id,
    )
    config = GatewayConfig()
    config.provider = request.provider
    gateway = ModelGateway(config=config)
    result = await gateway.generate(model_request)
    return {
        "text": result.response.text,
        "latency_ms": result.response.latency_ms,
        "provider": result.response.provider,
        "model": result.response.model,
        "usage": result.response.usage.__dict__,
        "request_id": result.response.request_id,
        "attempts": result.attempts,
    }


@app.get("/api/traces/{trace_id}")
async def api_trace(trace_id: str) -> dict:
    reader = TraceReader(Path(".xaiforge"), trace_id)
    try:
        return reader.load_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Trace not found") from exc


@app.get("/api/traces/{trace_id}/events")
async def api_trace_events(trace_id: str) -> list[dict]:
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
                except TimeoutError:
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
                except TimeoutError:
                    if task.done() and queue.empty():
                        break
        finally:
            await task

    return EventSourceResponse(event_stream())


@app.get("/api/experiments")
async def api_experiments() -> list[dict]:
    return [manifest.to_dict() for manifest in list_experiments()]


@app.get("/api/experiments/{experiment_id}")
async def api_experiment(experiment_id: str) -> dict:
    report_path = Path("reports") / "experiments" / f"{experiment_id}.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Experiment not found")
    return json.loads(report_path.read_text(encoding="utf-8"))


@app.post("/api/experiments/run")
async def api_experiment_run(request: ExperimentRunRequest) -> EventSourceResponse:
    async def event_stream() -> AsyncIterator[dict]:
        yield {"event": "message", "data": json.dumps({"status": "starting"})}

        def _run() -> dict:
            if request.request_template:
                template = request.request_template
                messages = [ModelMessage(**message) for message in template.get("messages", [])]
                tools = [ToolDefinition(**tool) for tool in template.get("tools", [])]
                request_template = ExperimentRequestTemplate(
                    messages=messages,
                    tools=tools,
                    tags=template.get("tags", []),
                    metadata=template.get("metadata", {}),
                    temperature=template.get("temperature", 0.2),
                    max_tokens=template.get("max_tokens", 512),
                    seed=template.get("seed"),
                    stop=template.get("stop"),
                )
            else:
                task = request.task or ""
                request_template = ExperimentRequestTemplate(
                    messages=[ModelMessage(role="user", content=task)]
                )
            config = ExperimentConfig.create(
                experiment_id=datetime.now(UTC).strftime("exp%Y%m%d%H%M%S%f"),
                mode=request.mode,  # type: ignore[arg-type]
                providers=request.providers,
                request_template=request_template,
                max_concurrency=request.max_concurrency,
                timeout_s=request.timeout_s,
            )
            result = run_experiment(config)
            manifest = save_experiment_artifacts(config, result)
            return manifest.to_dict()

        loop = asyncio.get_running_loop()
        manifest = await loop.run_in_executor(None, _run)
        yield {"event": "message", "data": json.dumps({"status": "completed", "manifest": manifest})}

    return EventSourceResponse(event_stream())


@app.post("/api/index/build")
async def api_index_build() -> dict:
    stats = build_index(Path(".xaiforge"))
    return stats.to_dict()


@app.get("/api/index/stats")
async def api_index_stats() -> dict:
    stats = load_index_stats(Path(".xaiforge"))
    if not stats:
        raise HTTPException(status_code=404, detail="Index not built")
    return stats.to_dict()


@app.get("/api/reports/evals")
async def api_reports_evals() -> list[str]:
    return _list_reports(Path("reports") / "evals")


@app.get("/api/reports/evals/{name}")
async def api_report_eval(name: str) -> dict:
    return _read_report(Path("reports") / "evals", name)


@app.get("/api/reports/perf")
async def api_reports_perf() -> list[str]:
    return _list_reports(Path("reports") / "perf")


@app.get("/api/reports/perf/{name}")
async def api_report_perf(name: str) -> dict:
    return _read_report(Path("reports") / "perf", name)


@app.get("/api/reports/experiments")
async def api_reports_experiments() -> list[str]:
    return _list_reports(Path("reports") / "experiments")


@app.get("/api/reports/experiments/{name}")
async def api_report_experiments(name: str) -> dict:
    return _read_report(Path("reports") / "experiments", name)


def _list_reports(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted([path.name for path in directory.glob("*.json")])


def _read_report(directory: Path, name: str) -> dict:
    if ".." in name or "/" in name:
        raise HTTPException(status_code=400, detail="Invalid report name")
    path = directory / name
    if not path.exists() or path.suffix != ".json":
        raise HTTPException(status_code=404, detail="Report not found")
    return json.loads(path.read_text(encoding="utf-8"))
