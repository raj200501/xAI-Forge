from __future__ import annotations

# fmt: off

# ruff: noqa: E501
# ruff: noqa: I001

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xaiforge.trace_store import TraceReader, list_manifests


@dataclass(frozen=True)
class IndexStats:
    trace_count: int
    event_count: int
    indexed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_count": self.trace_count,
            "event_count": self.event_count,
            "indexed_at": self.indexed_at,
        }


def build_index(base_dir: Path | None = None) -> IndexStats:
    base_dir = base_dir or Path(".xaiforge")
    db_path = base_dir / "index.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)
        manifests = list_manifests(base_dir)
        indexed = _existing_trace_ids(conn)
        trace_count = 0
        event_count = 0
        for manifest in manifests:
            trace_id = manifest.get("trace_id")
            if not trace_id or trace_id in indexed:
                continue
            trace_count += 1
            event_count += _index_trace(conn, base_dir, trace_id, manifest)
        indexed_at = datetime.utcnow().isoformat()
        _write_stats(conn, trace_count, event_count, indexed_at)
        conn.commit()
    finally:
        conn.close()
    return IndexStats(trace_count=trace_count, event_count=event_count, indexed_at=indexed_at)


def load_index_stats(base_dir: Path | None = None) -> IndexStats | None:
    base_dir = base_dir or Path(".xaiforge")
    db_path = base_dir / "index.sqlite"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT trace_count, event_count, indexed_at FROM stats LIMIT 1").fetchone()
        if not row:
            return None
        return IndexStats(trace_count=row[0], event_count=row[1], indexed_at=row[2])
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manifests (
            trace_id TEXT PRIMARY KEY,
            provider TEXT,
            started_at TEXT,
            duration REAL,
            tool_calls INTEGER,
            errors INTEGER,
            tags TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            ts TEXT,
            type TEXT,
            tool_name TEXT,
            hash TEXT,
            parent_span_id TEXT,
            searchable_text TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            trace_count INTEGER,
            event_count INTEGER,
            indexed_at TEXT
        )
        """
    )


def _existing_trace_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT trace_id FROM manifests").fetchall()
    return {row[0] for row in rows}


def _index_trace(
    conn: sqlite3.Connection,
    base_dir: Path,
    trace_id: str,
    manifest: dict[str, Any],
) -> int:
    tags = json.dumps(manifest.get("tags", []))
    conn.execute(
        """
        INSERT OR REPLACE INTO manifests (
            trace_id, provider, started_at, duration, tool_calls, errors, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id,
            manifest.get("provider"),
            manifest.get("started_at"),
            manifest.get("duration_s"),
            manifest.get("tool_call_count", 0),
            manifest.get("error_count", 0),
            tags,
        ),
    )
    reader = TraceReader(base_dir, trace_id)
    event_count = 0
    for line in reader.iter_events():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_count += 1
        conn.execute(
            """
            INSERT INTO events (
                trace_id, ts, type, tool_name, hash, parent_span_id, searchable_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                payload.get("ts"),
                payload.get("type"),
                payload.get("tool_name"),
                payload.get("span_id"),
                payload.get("parent_span_id"),
                _searchable_text(payload),
            ),
        )
    return event_count


def _searchable_text(payload: dict[str, Any]) -> str:
    parts = [payload.get("type", "")]
    for key in ("content", "tool_name", "error", "result"):
        value = payload.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def _write_stats(conn: sqlite3.Connection, trace_count: int, event_count: int, indexed_at: str) -> None:
    conn.execute("DELETE FROM stats")
    conn.execute(
        "INSERT INTO stats (trace_count, event_count, indexed_at) VALUES (?, ?, ?)",
        (trace_count, event_count, indexed_at),
    )
