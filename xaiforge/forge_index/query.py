from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xaiforge.query import Condition, parse_query


@dataclass(frozen=True)
class FastQueryResult:
    trace_id: str
    matches: int


def fast_query(base_dir: Path, expression: str) -> dict[str, int]:
    db_path = base_dir / "index.sqlite"
    if not db_path.exists():
        raise FileNotFoundError("Index database not found")
    conditions = _parse_extended(expression)
    conn = sqlite3.connect(db_path)
    try:
        return _query(conn, conditions)
    finally:
        conn.close()


def _query(conn: sqlite3.Connection, conditions: list[Condition]) -> dict[str, int]:
    clauses = []
    params: list[Any] = []
    for condition in conditions:
        if condition.field == "started_at":
            clauses.append("manifests.started_at >= ?")
            params.append(condition.value)
            continue
        if condition.field == "ended_at":
            clauses.append("manifests.started_at <= ?")
            params.append(condition.value)
            continue
        if condition.field == "tag":
            clauses.append("manifests.tags LIKE ?")
            params.append(f"%{condition.value}%")
            continue
        if condition.operator == "=":
            clauses.append("events.type = ?")
            params.append(condition.value)
        elif condition.operator == "~":
            clauses.append("events.searchable_text LIKE ?")
            params.append(f"%{condition.value}%")
    sql = (
        "SELECT events.trace_id, COUNT(*) FROM events "
        "JOIN manifests ON manifests.trace_id = events.trace_id"
    )
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " GROUP BY events.trace_id"
    rows = conn.execute(sql, params).fetchall()
    return {row[0]: row[1] for row in rows}


def _parse_extended(expression: str) -> list[Condition]:
    conditions = parse_query(expression)
    expanded: list[Condition] = []
    for condition in conditions:
        field = condition.field
        if field in {"started_at", "ended_at"}:
            expanded.append(condition)
            continue
        if field == "tag":
            expanded.append(condition)
            continue
        expanded.append(condition)
    return expanded


_unused_datetime = datetime.utcnow
_unused_json = json.dumps
