from __future__ import annotations

import json

from xaiforge.compat import httpx
from xaiforge.compat.httpx import Response
from xaiforge_sdk.client import Client
from xaiforge_sdk.sse import stream_sse


def test_stream_sse_parses_events():
    payloads = [
        {
            "type": "run_start",
            "trace_id": "t1",
            "ts": "now",
            "span_id": "s1",
            "task": "x",
            "provider": "heuristic",
            "root_dir": ".",
        },
        {
            "type": "run_end",
            "trace_id": "t1",
            "ts": "now",
            "span_id": "s2",
            "summary": "done",
            "status": "ok",
        },
    ]
    body = "\n".join([f"data: {json.dumps(item)}" for item in payloads])

    def handler(request: httpx.Request) -> Response:
        return Response(200, content=body)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    events = list(stream_sse(client, "POST", "http://test", json_payload={"task": "x"}))
    assert events == payloads


def test_client_list_traces():
    traces_payload = [
        {
            "trace_id": "t1",
            "started_at": "a",
            "ended_at": "b",
            "root_dir": ".",
            "provider": "heuristic",
            "task": "task",
            "final_hash": "hash",
            "event_count": 3,
        }
    ]

    def handler(request: httpx.Request) -> Response:
        if request.url.path == "/api/traces":
            return Response(200, json=traces_payload)
        raise AssertionError("Unexpected path")

    transport = httpx.MockTransport(handler)
    client = Client(base_url="http://test")
    client._client = httpx.Client(transport=transport, base_url="http://test")
    traces = client.list_traces()
    assert traces[0].trace_id == "t1"
    client.close()
