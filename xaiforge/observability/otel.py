from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OtelConfig:
    enabled: bool = False
    service_name: str = "xaiforge"

    @classmethod
    def from_env(cls) -> OtelConfig:
        enabled = os.getenv("XAIFORGE_ENABLE_OTEL", "0") == "1"
        service_name = os.getenv("XAIFORGE_SERVICE_NAME", "xaiforge")
        return cls(enabled=enabled, service_name=service_name)


def _otel_available() -> bool:
    return importlib.util.find_spec("opentelemetry") is not None


def configure_otel(config: OtelConfig | None = None) -> bool:
    config = config or OtelConfig.from_env()
    if not config.enabled:
        return False
    if not _otel_available():
        return False
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: config.service_name}))
    trace.set_tracer_provider(provider)
    return True
