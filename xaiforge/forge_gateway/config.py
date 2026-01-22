from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from xaiforge.forge_gateway.batching import BatchConfig
from xaiforge.forge_gateway.reliability import RetryPolicy


@dataclass
class GatewayConfig:
    provider: str = "mock"
    model: str = "mock-001"
    timeout_s: float = 10.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    batch: BatchConfig = field(default_factory=BatchConfig)
    circuit_breaker: bool = False
    circuit_failures: int = 3
    circuit_reset_s: float = 5.0
    safety_enabled: bool = False


DEFAULT_CONFIG_PATH = Path.home() / ".xaiforge" / "gateway.json"


def load_gateway_config(path: Path | None = None) -> GatewayConfig:
    config_path = path or Path(os.getenv("XAIFORGE_GATEWAY_CONFIG", str(DEFAULT_CONFIG_PATH)))
    data: dict[str, object] = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    env_provider = os.getenv("XAIFORGE_GATEWAY_PROVIDER")
    env_model = os.getenv("XAIFORGE_GATEWAY_MODEL")
    env_timeout = os.getenv("XAIFORGE_GATEWAY_TIMEOUT")
    env_batch = os.getenv("XAIFORGE_GATEWAY_BATCH")
    env_batch_size = os.getenv("XAIFORGE_GATEWAY_BATCH_SIZE")
    env_batch_wait = os.getenv("XAIFORGE_GATEWAY_BATCH_WAIT_MS")

    config = GatewayConfig(
        provider=str(data.get("provider", env_provider or "mock")),
        model=str(data.get("model", env_model or "mock-001")),
        timeout_s=float(data.get("timeout_s", env_timeout or 10.0)),
        retry=RetryPolicy(
            max_attempts=int(data.get("retry", {}).get("max_attempts", 3)),
            base_delay_s=float(data.get("retry", {}).get("base_delay_s", 0.2)),
            max_delay_s=float(data.get("retry", {}).get("max_delay_s", 2.0)),
            jitter=float(data.get("retry", {}).get("jitter", 0.1)),
        ),
        batch=BatchConfig(
            enabled=bool(data.get("batch", {}).get("enabled", env_batch == "1")),
            max_batch_size=int(data.get("batch", {}).get("max_batch_size", env_batch_size or 4)),
            max_wait_ms=int(data.get("batch", {}).get("max_wait_ms", env_batch_wait or 25)),
        ),
        circuit_breaker=bool(data.get("circuit_breaker", False)),
        circuit_failures=int(data.get("circuit_failures", 3)),
        circuit_reset_s=float(data.get("circuit_reset_s", 5.0)),
        safety_enabled=bool(data.get("safety_enabled", False)),
    )
    return config
