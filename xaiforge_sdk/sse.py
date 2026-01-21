from __future__ import annotations

import json
from collections.abc import Iterator

from xaiforge.compat import httpx


def stream_sse(
    client: httpx.Client,
    method: str,
    url: str,
    json_payload: dict | None = None,
) -> Iterator[dict]:
    with client.stream(method, url, json=json_payload) as response:
        response.raise_for_status()
        buffer = ""
        for chunk in response.iter_text():
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line.removeprefix("data:").strip()
                    if data:
                        yield json.loads(data)
        if buffer.strip().startswith("data:"):
            data = buffer.strip().removeprefix("data:").strip()
            if data:
                yield json.loads(data)
