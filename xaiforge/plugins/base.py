from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xaiforge.events import Event


@dataclass(frozen=True)
class PluginContext:
    trace_id: str
    base_dir: Path
    task: str
    provider: str
    root: Path
    started_at: str


class Plugin(Protocol):
    name: str

    def on_run_start(self, context: PluginContext, event: Event) -> Event:
        ...

    def on_event(self, context: PluginContext, event: Event) -> Event:
        ...

    def on_run_end(self, context: PluginContext, event: Event) -> Event:
        ...


class BasePlugin:
    name = "base"

    def on_run_start(self, context: PluginContext, event: Event) -> Event:
        return event

    def on_event(self, context: PluginContext, event: Event) -> Event:
        return event

    def on_run_end(self, context: PluginContext, event: Event) -> Event:
        return event
