from __future__ import annotations

from collections.abc import Iterator

from xaiforge.compat import httpx
from xaiforge.compat.pydantic import TypeAdapter
from xaiforge_sdk.models import Event, RunRequest, TraceManifest
from xaiforge_sdk.sse import stream_sse


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._event_adapter = TypeAdapter(Event)

    def close(self) -> None:
        self._client.close()

    def list_traces(self) -> list[TraceManifest]:
        response = self._client.get("/api/traces")
        response.raise_for_status()
        return [TraceManifest.model_validate(item) for item in response.json()]

    def get_trace(self, trace_id: str) -> TraceManifest:
        response = self._client.get(f"/api/traces/{trace_id}")
        response.raise_for_status()
        return TraceManifest.model_validate(response.json())

    def get_events(self, trace_id: str) -> list[Event]:
        response = self._client.get(f"/api/traces/{trace_id}/events")
        response.raise_for_status()
        payload = response.json()
        return [self._event_adapter.validate_python(item) for item in payload]

    def start_run(
        self,
        task: str,
        root: str = ".",
        provider: str = "heuristic",
        allow_net: bool = False,
        plugins: list[str] | None = None,
    ) -> Iterator[Event]:
        request = RunRequest(
            task=task,
            root=root,
            provider=provider,
            allow_net=allow_net,
            plugins=plugins or [],
        )
        for payload in stream_sse(
            self._client, "POST", f"{self.base_url}/api/run", request.model_dump()
        ):
            yield self._event_adapter.validate_python(payload)

    def replay(self, trace_id: str) -> Iterator[Event]:
        for payload in stream_sse(
            self._client, "POST", f"{self.base_url}/api/replay/{trace_id}", None
        ):
            yield self._event_adapter.validate_python(payload)
