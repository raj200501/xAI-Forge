from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xaiforge.events import Event, RollingHasher


@dataclass
class TraceManifest:
    trace_id: str
    started_at: str
    ended_at: str
    root_dir: str
    provider: str
    task: str
    final_hash: str
    event_count: int

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "root_dir": self.root_dir,
            "provider": self.provider,
            "task": self.task,
            "final_hash": self.final_hash,
            "event_count": self.event_count,
        }


class TraceStore:
    def __init__(self, base_dir: Path, trace_id: str) -> None:
        self.base_dir = base_dir
        self.trace_id = trace_id
        self.trace_dir = base_dir / "traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.trace_dir / f"{trace_id}.jsonl"
        self._file = self.path.open("w", encoding="utf-8")
        self.hasher = RollingHasher()
        self.event_count = 0

    def write_event(self, event: Event) -> None:
        line = event.to_json()
        self._file.write(line + "\n")
        self._file.flush()
        if event.type != "run_end":
            self.hasher.update(line)
        self.event_count += 1

    def close(self) -> None:
        self._file.close()

    def write_manifest(self, manifest: TraceManifest) -> None:
        manifest_path = self.trace_dir / f"{self.trace_id}.manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

    def write_report(self, summary: str) -> None:
        report_path = self.trace_dir / f"{self.trace_id}.report.md"
        report_path.write_text(summary, encoding="utf-8")


class TraceReader:
    def __init__(self, base_dir: Path, trace_id: str) -> None:
        self.base_dir = base_dir
        self.trace_id = trace_id
        self.trace_dir = base_dir / "traces"
        self.path = self.trace_dir / f"{trace_id}.jsonl"
        self.manifest_path = self.trace_dir / f"{trace_id}.manifest.json"

    def iter_events(self) -> Iterable[str]:
        with self.path.open("r", encoding="utf-8") as handle:
            yield from handle

    def load_manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))


def list_manifests(base_dir: Path) -> list[dict]:
    trace_dir = base_dir / "traces"
    if not trace_dir.exists():
        return []
    manifests = []
    for manifest_path in trace_dir.glob("*.manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        trace_id = manifest.get("trace_id")
        trace_path = trace_dir / f"{trace_id}.jsonl"
        tool_calls, error_count = _summarize_trace(trace_path)
        manifest["tool_call_count"] = tool_calls
        manifest["error_count"] = error_count
        manifest["duration_s"] = _duration_seconds(
            manifest.get("started_at"), manifest.get("ended_at")
        )
        manifests.append(manifest)
    manifests.sort(key=lambda item: item.get("started_at", ""), reverse=True)
    return manifests


def _duration_seconds(started_at: str | None, ended_at: str | None) -> float | None:
    if not started_at or not ended_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
        ended = datetime.fromisoformat(ended_at)
    except ValueError:
        return None
    duration = (ended - started).total_seconds()
    return max(duration, 0.0)


def _summarize_trace(trace_path: Path) -> tuple[int, int]:
    if not trace_path.exists():
        return 0, 0
    tool_calls = 0
    error_count = 0
    with trace_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = payload.get("type")
            if event_type == "tool_call":
                tool_calls += 1
            if event_type == "tool_error":
                error_count += 1
    return tool_calls, error_count
