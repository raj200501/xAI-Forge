from __future__ import annotations

import importlib
import importlib.util
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class EventSourceResponse:
    event_source: AsyncIterator[dict[str, Any]]

    def __iter__(self):
        return iter(())


_SSE_SPEC = importlib.util.find_spec("sse_starlette")
if _SSE_SPEC is not None:
    EventSourceResponse = importlib.import_module("sse_starlette.sse").EventSourceResponse
