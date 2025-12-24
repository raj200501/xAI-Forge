from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from xaiforge.events import Message, RunEnd, RunStart
from xaiforge.providers.base import Provider
from xaiforge.providers.heuristic import HeuristicProvider
from xaiforge.providers.ollama import OllamaProvider
from xaiforge.providers.openai_compat import OpenAICompatibleProvider
from xaiforge.tools.registry import ToolContext, ToolRegistry, build_registry
from xaiforge.trace_store import TraceManifest, TraceStore


PROVIDERS = {
    "heuristic": HeuristicProvider(),
    "ollama": OllamaProvider(),
    "openai_compat": OpenAICompatibleProvider(),
}


def get_provider(name: str) -> Provider:
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")
    return PROVIDERS[name]


class EventEmitter:
    def __init__(self, store: TraceStore) -> None:
        self.store = store

    async def emit(self, event) -> None:
        self.store.write_event(event)


async def run_task(
    task: str,
    provider_name: str,
    root: Path,
    allow_net: bool,
) -> TraceManifest:
    trace_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    base_dir = Path(".xaiforge")
    store = TraceStore(base_dir, trace_id)
    tools = build_registry()
    context = ToolContext(root=root, allow_net=allow_net, trace_id=trace_id)
    emitter = EventEmitter(store)
    started_at = datetime.now(timezone.utc).isoformat()
    await emitter.emit(
        RunStart(
            trace_id=trace_id,
            task=task,
            provider=provider_name,
            root_dir=str(root),
        )
    )
    provider = get_provider(provider_name)
    try:
        final_answer = await provider.run(task, tools, context, emitter.emit)
        status = "ok"
    except Exception as exc:
        final_answer = f"Run failed: {exc}"
        status = "error"
        await emitter.emit(
            Message(
                trace_id=trace_id,
                role="assistant",
                content=final_answer,
            )
        )
    ended_at = datetime.now(timezone.utc).isoformat()
    final_hash = store.hasher.hexdigest
    await emitter.emit(
        RunEnd(
            trace_id=trace_id,
            status=status,
            summary=final_answer,
            final_hash=final_hash,
            event_count=store.event_count + 1,
        )
    )
    store.close()
    manifest = TraceManifest(
        trace_id=trace_id,
        started_at=started_at,
        ended_at=ended_at,
        root_dir=str(root),
        provider=provider_name,
        task=task,
        final_hash=final_hash,
        event_count=store.event_count,
    )
    store.write_manifest(manifest)
    store.write_report(
        f"# Trace {trace_id}\n\n"
        f"- Task: {task}\n"
        f"- Provider: {provider_name}\n"
        f"- Started: {started_at}\n"
        f"- Ended: {ended_at}\n"
        f"- Events: {store.event_count}\n"
        f"- Final hash: `{final_hash}`\n\n"
        f"## Summary\n\n{final_answer}\n"
    )
    return manifest


async def stream_run(
    task: str,
    provider_name: str,
    root: Path,
    allow_net: bool,
    on_event: Callable[[str], None],
) -> TraceManifest:
    trace_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    base_dir = Path(".xaiforge")
    store = TraceStore(base_dir, trace_id)
    tools = build_registry()
    context = ToolContext(root=root, allow_net=allow_net, trace_id=trace_id)
    emitter = EventEmitter(store)
    started_at = datetime.now(timezone.utc).isoformat()

    async def emit_and_forward(event) -> None:
        emitter.store.write_event(event)
        on_event(event.to_json())

    await emit_and_forward(
        RunStart(
            trace_id=trace_id,
            task=task,
            provider=provider_name,
            root_dir=str(root),
        )
    )
    provider = get_provider(provider_name)
    try:
        final_answer = await provider.run(task, tools, context, emit_and_forward)
        status = "ok"
    except Exception as exc:
        final_answer = f"Run failed: {exc}"
        status = "error"
        await emit_and_forward(
            Message(
                trace_id=trace_id,
                role="assistant",
                content=final_answer,
            )
        )
    ended_at = datetime.now(timezone.utc).isoformat()
    final_hash = store.hasher.hexdigest
    await emit_and_forward(
        RunEnd(
            trace_id=trace_id,
            status=status,
            summary=final_answer,
            final_hash=final_hash,
            event_count=store.event_count + 1,
        )
    )
    store.close()
    manifest = TraceManifest(
        trace_id=trace_id,
        started_at=started_at,
        ended_at=ended_at,
        root_dir=str(root),
        provider=provider_name,
        task=task,
        final_hash=final_hash,
        event_count=store.event_count,
    )
    store.write_manifest(manifest)
    store.write_report(
        f"# Trace {trace_id}\n\n"
        f"- Task: {task}\n"
        f"- Provider: {provider_name}\n"
        f"- Started: {started_at}\n"
        f"- Ended: {ended_at}\n"
        f"- Events: {store.event_count}\n"
        f"- Final hash: `{final_hash}`\n\n"
        f"## Summary\n\n{final_answer}\n"
    )
    return manifest


async def replay_trace(trace_id: str, on_event: Callable[[str], None]) -> RunEnd:
    base_dir = Path(".xaiforge")
    from xaiforge.trace_store import TraceReader

    reader = TraceReader(base_dir, trace_id)
    manifest = reader.load_manifest()
    from xaiforge.events import RollingHasher

    hasher = RollingHasher()
    count = 0
    for raw in reader.iter_events():
        line = raw.rstrip("\n")
        if not line:
            continue
        on_event(line)
        try:
            import json

            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {}
        if payload.get("type") != "run_end":
            hasher.update(line)
        count += 1
    final_hash = hasher.hexdigest
    integrity_ok = final_hash == manifest.get("final_hash")
    run_end = RunEnd(
        trace_id=trace_id,
        status="ok" if integrity_ok else "error",
        summary="Replay complete",
        final_hash=final_hash,
        event_count=count,
        integrity_ok=integrity_ok,
    )
    on_event(run_end.to_json())
    return run_end
