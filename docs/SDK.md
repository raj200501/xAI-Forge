# Python SDK

The `xaiforge_sdk` package provides a typed client for the API with streaming support.

## Install

```bash
pip install -e ".[sdk]"
```

## Usage

```python
from xaiforge_sdk import Client

client = Client("http://127.0.0.1:8000")

for event in client.start_run("Summarize the repo"):
    print(event.type, event.ts)

trace = client.list_traces()[0]
print(trace.trace_id)
```

## Streaming helpers

The SDK includes an SSE iterator helper (`xaiforge_sdk.sse.stream_sse`) used internally by
`Client.start_run` and `Client.replay`.
