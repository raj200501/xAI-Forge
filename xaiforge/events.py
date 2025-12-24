from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter

EventType = Literal[
    "run_start",
    "plan",
    "message",
    "tool_call",
    "tool_result",
    "tool_error",
    "run_end",
]


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid4().hex


class EventBase(BaseModel):
    trace_id: str
    ts: str = Field(default_factory=now_ts)
    type: EventType
    span_id: str = Field(default_factory=new_id)
    parent_span_id: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()


class RunStart(EventBase):
    type: Literal["run_start"] = "run_start"
    task: str
    provider: str
    root_dir: str


class Plan(EventBase):
    type: Literal["plan"] = "plan"
    steps: list[str]


class Message(EventBase):
    type: Literal["message"] = "message"
    role: Literal["system", "assistant", "tool"]
    content: str


class ToolCall(EventBase):
    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: Dict[str, Any]


class ToolResult(EventBase):
    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    result: Any


class ToolError(EventBase):
    type: Literal["tool_error"] = "tool_error"
    tool_name: str
    error: str


class RunEnd(EventBase):
    type: Literal["run_end"] = "run_end"
    status: Literal["ok", "error"] = "ok"
    summary: str
    final_hash: Optional[str] = None
    event_count: Optional[int] = None
    integrity_ok: Optional[bool] = None


Event = RunStart | Plan | Message | ToolCall | ToolResult | ToolError | RunEnd


def event_schema() -> Dict[str, Any]:
    adapter = TypeAdapter(Event)
    return adapter.json_schema()


class RollingHasher:
    def __init__(self) -> None:
        self._hash = hashlib.sha256()
        self.count = 0

    def update(self, line: str) -> None:
        data = (line + "\n").encode("utf-8")
        self._hash.update(data)
        self.count += 1

    @property
    def hexdigest(self) -> str:
        return self._hash.hexdigest()
