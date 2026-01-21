from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from xaiforge.benchmarks.report import write_bench_report
from xaiforge.events import Message, RunEnd, RunStart
from xaiforge.observability.logging import LoggingConfig, configure_logging
from xaiforge.observability.otel import configure_otel
from xaiforge.observability.run_metrics import RunMetrics
from xaiforge.plugins.base import PluginContext
from xaiforge.plugins.registry import load_plugins
from xaiforge.policy.loader import load_policy_from_env
from xaiforge.providers.base import Provider
from xaiforge.providers.heuristic import HeuristicProvider
from xaiforge.providers.ollama import OllamaProvider
from xaiforge.providers.openai_compat import OpenAICompatibleProvider
from xaiforge.tools.policy_registry import PolicyToolRegistry
from xaiforge.tools.registry import ToolContext, build_registry
from xaiforge.trace_store import TraceManifest, TraceReader, TraceStore

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


def _configure_observability() -> None:
    if os.getenv("XAIFORGE_ENABLE_LOGGING") == "1":
        configure_logging(LoggingConfig.from_env())
    if os.getenv("XAIFORGE_ENABLE_OTEL") == "1":
        configure_otel()


def _init_metrics(trace_id: str) -> RunMetrics | None:
    if os.getenv("XAIFORGE_ENABLE_METRICS") == "1":
        return RunMetrics(trace_id=trace_id)
    return None


async def run_task(
    task: str,
    provider_name: str,
    root: Path,
    allow_net: bool,
    plugins: list[str] | None = None,
) -> TraceManifest:
    trace_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    _configure_observability()
    metrics = _init_metrics(trace_id)
    base_dir = Path(".xaiforge")
    store = TraceStore(base_dir, trace_id)
    tools = build_registry()
    policy = load_policy_from_env()
    if policy:
        policy.attach_trace(trace_id)
        tools = PolicyToolRegistry(tools, policy)
    context = ToolContext(root=root, allow_net=allow_net, trace_id=trace_id)
    emitter = EventEmitter(store)
    started_at = datetime.now(UTC).isoformat()
    plugin_instances = load_plugins(plugins or [])
    plugin_context = PluginContext(
        trace_id=trace_id,
        base_dir=base_dir,
        task=task,
        provider=provider_name,
        root=root,
        started_at=started_at,
    )

    def _apply_event_plugins(event):
        for plugin in plugin_instances:
            event = plugin.on_event(plugin_context, event)
        return event

    run_start = RunStart(
        trace_id=trace_id,
        task=task,
        provider=provider_name,
        root_dir=str(root),
    )
    for plugin in plugin_instances:
        run_start = plugin.on_run_start(plugin_context, run_start)
    run_start = _apply_event_plugins(run_start)
    if metrics:
        metrics.record_event(run_start.type)
    await emitter.emit(run_start)
    provider = get_provider(provider_name)
    try:

        async def emit(event) -> None:
            event = _apply_event_plugins(event)
            if metrics:
                metrics.record_event(event.type)
                if event.type == "tool_result":
                    metrics.record_tool(getattr(event, "tool_name", "unknown"), "ok")
                if event.type == "tool_error":
                    metrics.record_tool(getattr(event, "tool_name", "unknown"), "error")
            await emitter.emit(event)

        final_answer = await provider.run(task, tools, context, emit)
        status = "ok"
    except Exception as exc:
        final_answer = f"Run failed: {exc}"
        status = "error"
        message = Message(
            trace_id=trace_id,
            role="assistant",
            content=final_answer,
        )
        message = _apply_event_plugins(message)
        if metrics:
            metrics.record_event(message.type)
        await emitter.emit(message)
    ended_at = datetime.now(UTC).isoformat()
    final_hash = store.hasher.hexdigest
    run_end = RunEnd(
        trace_id=trace_id,
        status=status,
        summary=final_answer,
        final_hash=final_hash,
        event_count=store.event_count + 1,
    )
    for plugin in plugin_instances:
        run_end = plugin.on_run_end(plugin_context, run_end)
    run_end = _apply_event_plugins(run_end)
    if metrics:
        metrics.record_event(run_end.type)
    await emitter.emit(run_end)
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
    if policy:
        policy_report_path = base_dir / "policy" / f"{trace_id}.json"
        policy.report().write_json(policy_report_path)
    if metrics:
        metrics.write(base_dir)
    reader = TraceReader(base_dir, trace_id)
    events = [json.loads(line) for line in reader.iter_events() if line.strip()]
    write_bench_report(base_dir, manifest.to_dict(), events)
    return manifest


async def stream_run(
    task: str,
    provider_name: str,
    root: Path,
    allow_net: bool,
    on_event: Callable[[str], None],
    plugins: list[str] | None = None,
) -> TraceManifest:
    trace_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    _configure_observability()
    metrics = _init_metrics(trace_id)
    base_dir = Path(".xaiforge")
    store = TraceStore(base_dir, trace_id)
    tools = build_registry()
    policy = load_policy_from_env()
    if policy:
        policy.attach_trace(trace_id)
        tools = PolicyToolRegistry(tools, policy)
    context = ToolContext(root=root, allow_net=allow_net, trace_id=trace_id)
    emitter = EventEmitter(store)
    started_at = datetime.now(UTC).isoformat()
    plugin_instances = load_plugins(plugins or [])
    plugin_context = PluginContext(
        trace_id=trace_id,
        base_dir=base_dir,
        task=task,
        provider=provider_name,
        root=root,
        started_at=started_at,
    )

    async def emit_and_forward(event) -> None:
        for plugin in plugin_instances:
            event = plugin.on_event(plugin_context, event)
        if metrics:
            metrics.record_event(event.type)
            if event.type == "tool_result":
                metrics.record_tool(getattr(event, "tool_name", "unknown"), "ok")
            if event.type == "tool_error":
                metrics.record_tool(getattr(event, "tool_name", "unknown"), "error")
        emitter.store.write_event(event)
        on_event(event.to_json())

    run_start = RunStart(
        trace_id=trace_id,
        task=task,
        provider=provider_name,
        root_dir=str(root),
    )
    for plugin in plugin_instances:
        run_start = plugin.on_run_start(plugin_context, run_start)
    await emit_and_forward(run_start)
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
    ended_at = datetime.now(UTC).isoformat()
    final_hash = store.hasher.hexdigest
    run_end = RunEnd(
        trace_id=trace_id,
        status=status,
        summary=final_answer,
        final_hash=final_hash,
        event_count=store.event_count + 1,
    )
    for plugin in plugin_instances:
        run_end = plugin.on_run_end(plugin_context, run_end)
    await emit_and_forward(run_end)
    store.close()
    ended_at = datetime.now(UTC).isoformat()
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
    if policy:
        policy_report_path = base_dir / "policy" / f"{trace_id}.json"
        policy.report().write_json(policy_report_path)
    if metrics:
        metrics.write(base_dir)
    reader = TraceReader(base_dir, trace_id)
    events = [json.loads(line) for line in reader.iter_events() if line.strip()]
    write_bench_report(base_dir, manifest.to_dict(), events)
    return manifest
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
