from pathlib import Path

from xaiforge.events import Message
from xaiforge.trace_store import TraceStore


def test_trace_store_hash_excludes_run_end(tmp_path: Path) -> None:
    store = TraceStore(tmp_path, "trace123")
    event = Message(trace_id="trace123", role="assistant", content="hi")
    store.write_event(event)
    store.close()
    assert store.hasher.hexdigest
    assert store.event_count == 1
