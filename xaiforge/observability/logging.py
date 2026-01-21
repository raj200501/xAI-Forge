from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    format: str = "plain"
    service: str = "xaiforge"
    include_context: bool = True
    redact_keys: tuple[str, ...] = (
        "authorization",
        "api_key",
        "token",
        "secret",
    )

    @classmethod
    def from_env(cls) -> LoggingConfig:
        level = os.getenv("XAIFORGE_LOG_LEVEL", "INFO").upper()
        log_format = os.getenv("XAIFORGE_LOG_FORMAT", "plain").lower()
        include_context = os.getenv("XAIFORGE_LOG_CONTEXT", "1") == "1"
        service = os.getenv("XAIFORGE_SERVICE_NAME", "xaiforge")
        return cls(level=level, format=log_format, include_context=include_context, service=service)


class _JsonFormatter(logging.Formatter):
    def __init__(self, config: LoggingConfig) -> None:
        super().__init__()
        self.config = config

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.config.service,
        }
        if self.config.include_context:
            payload["context"] = _sanitize_context(record.__dict__, self.config.redact_keys)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _sanitize_context(context: Mapping[str, Any], redact_keys: tuple[str, ...]) -> dict[str, Any]:
    filtered = {}
    for key, value in context.items():
        if key.startswith("_"):
            continue
        if key in {"msg", "args", "message", "exc_info", "exc_text"}:
            continue
        if isinstance(key, str) and key.lower() in redact_keys:
            filtered[key] = "[redacted]"
        else:
            filtered[key] = _safe_json_value(value)
    return filtered


def _safe_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_json_value(val) for key, val in value.items()}
    return str(value)


def configure_logging(config: LoggingConfig | None = None) -> None:
    config = config or LoggingConfig.from_env()
    root_logger = logging.getLogger()
    level = getattr(logging, config.level, logging.INFO)
    root_logger.setLevel(level)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        root_logger.addHandler(handler)
    for handler in root_logger.handlers:
        if config.format == "json":
            handler.setFormatter(_JsonFormatter(config))
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
