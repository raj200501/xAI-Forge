from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

EventType = Literal[
    "run_start",
    "plan",
    "message",
    "tool_call",
    "tool_result",
    "tool_error",
    "run_end",
]


class TraceManifest(BaseModel):
    trace_id: str
    started_at: str
    ended_at: str
    root_dir: str
    provider: str
    task: str
    final_hash: str
    event_count: int


class EventBase(BaseModel):
    trace_id: str
    ts: str
    type: EventType
    span_id: str
    parent_span_id: Optional[str] = None


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


class RunRequest(BaseModel):
    task: str
    root: str = "."
    provider: str = "heuristic"
    allow_net: bool = False
    plugins: list[str] = Field(default_factory=list)
