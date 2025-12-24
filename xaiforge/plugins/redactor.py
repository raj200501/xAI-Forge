from __future__ import annotations

import re
from typing import Any

from xaiforge.events import Event
from xaiforge.plugins.base import BasePlugin, PluginContext

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TOKEN_RE = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|xai-[A-Za-z0-9]{16,})\b")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*")
_SECRET_KEYS = {"api_key", "token", "authorization", "secret"}


def _redact_string(value: str) -> str:
    value = _EMAIL_RE.sub("[redacted-email]", value)
    value = _TOKEN_RE.sub("[redacted-token]", value)
    value = _BEARER_RE.sub("Bearer [redacted-token]", value)
    return value


def _redact_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return _redact_string(payload)
    if isinstance(payload, list):
        return [_redact_payload(item) for item in payload]
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in _SECRET_KEYS:
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = _redact_payload(value)
        return sanitized
    return payload


class Redactor(BasePlugin):
    name = "redactor"

    def on_event(self, context: PluginContext, event: Event) -> Event:
        payload = event.model_dump()
        sanitized = _redact_payload(payload)
        return event.__class__(**sanitized)
