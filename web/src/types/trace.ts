export type EventType =
  | "run_start"
  | "plan"
  | "message"
  | "tool_call"
  | "tool_result"
  | "tool_error"
  | "run_end";

export interface TraceManifest {
  trace_id: string;
  task: string;
  provider: string;
  started_at: string;
  ended_at?: string;
  root_dir?: string;
  final_hash?: string;
  event_count?: number;
  duration_s?: number;
  tool_call_count?: number;
  error_count?: number;
}

export interface TraceEventBase {
  trace_id: string;
  ts: string;
  type: EventType;
  span_id?: string;
  parent_span_id?: string | null;
}

export interface TraceEvent extends TraceEventBase {
  [key: string]: unknown;
}

export interface ToolSpec {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface MetricsSummary {
  duration_s: number | null;
  event_count: number;
  tool_call_count: number;
  error_count: number;
  events_per_sec: number | null;
  top_tools: Array<{ name: string; count: number }>;
}
