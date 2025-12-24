from __future__ import annotations

from typing import Iterable

from xaiforge.plugins.base import BasePlugin
from xaiforge.plugins.metrics_collector import MetricsCollector
from xaiforge.plugins.redactor import Redactor


PLUGIN_FACTORIES = {
    "metrics_collector": MetricsCollector,
    "redactor": Redactor,
}


def available_plugins() -> list[str]:
    return sorted(PLUGIN_FACTORIES.keys())


def load_plugins(names: Iterable[str]) -> list[BasePlugin]:
    plugins = []
    for name in names:
        factory = PLUGIN_FACTORIES.get(name)
        if not factory:
            raise ValueError(f"Unknown plugin: {name}")
        plugins.append(factory())
    return plugins
