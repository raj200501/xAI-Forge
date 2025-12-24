import type { MetricsSummary, TraceEvent, TraceManifest } from "../types/trace";

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "–";
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const mins = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${mins}m ${rem.toFixed(1)}s`;
}

export function parseIsoDuration(startedAt?: string, endedAt?: string): number | null {
  if (!startedAt || !endedAt) return null;
  const start = Date.parse(startedAt);
  const end = Date.parse(endedAt);
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return Math.max(0, (end - start) / 1000);
}

export function computeMetrics(events: TraceEvent[], manifest?: TraceManifest): MetricsSummary {
  const toolCounts: Record<string, number> = {};
  let toolCalls = 0;
  let errors = 0;
  for (const event of events) {
    if (event.type === "tool_call") {
      toolCalls += 1;
      const name = String(event.tool_name ?? "unknown");
      toolCounts[name] = (toolCounts[name] || 0) + 1;
    }
    if (event.type === "tool_error") {
      errors += 1;
    }
  }
  const duration =
    parseIsoDuration(manifest?.started_at, manifest?.ended_at) ??
    parseIsoDuration(events[0]?.ts, events[events.length - 1]?.ts);
  const eventsPerSec = duration && duration > 0 ? events.length / duration : null;
  const topTools = Object.entries(toolCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }));
  return {
    duration_s: duration,
    event_count: events.length,
    tool_call_count: toolCalls,
    error_count: errors,
    events_per_sec: eventsPerSec,
    top_tools: topTools,
  };
}

export function formatTimestamp(ts?: string): string {
  if (!ts) return "–";
  const date = new Date(ts);
  if (Number.isNaN(date.valueOf())) return ts;
  return date.toLocaleString();
}

export function filterManifests(
  manifests: TraceManifest[],
  {
    query,
    provider,
    durationMin,
    durationMax,
    toolCallsMin,
  }: {
    query: string;
    provider: string;
    durationMin: string;
    durationMax: string;
    toolCallsMin: string;
  },
): TraceManifest[] {
  return manifests.filter((manifest) => {
    const needle = query.toLowerCase();
    const haystack = `${manifest.trace_id} ${manifest.task} ${manifest.provider}`.toLowerCase();
    if (needle && !haystack.includes(needle)) return false;
    if (provider !== "all" && manifest.provider !== provider) return false;
    const duration = manifest.duration_s ?? parseIsoDuration(manifest.started_at, manifest.ended_at);
    const min = durationMin ? Number(durationMin) : null;
    const max = durationMax ? Number(durationMax) : null;
    if (min != null && duration != null && duration < min) return false;
    if (max != null && duration != null && duration > max) return false;
    const toolCalls = manifest.tool_call_count ?? 0;
    if (toolCallsMin && toolCalls < Number(toolCallsMin)) return false;
    return true;
  });
}

export function buildSpanTree(events: TraceEvent[]): Array<{ event: TraceEvent; depth: number }>{
  const nodes = new Map<string, { event: TraceEvent; children: string[] }>();
  const roots: string[] = [];
  for (const event of events) {
    const spanId = event.span_id;
    if (!spanId) continue;
    if (!nodes.has(spanId)) {
      nodes.set(spanId, { event, children: [] });
    } else {
      nodes.get(spanId)!.event = event;
    }
  }
  for (const event of events) {
    const spanId = event.span_id;
    if (!spanId) continue;
    const parentId = event.parent_span_id;
    if (parentId && nodes.has(parentId)) {
      nodes.get(parentId)!.children.push(spanId);
    } else {
      roots.push(spanId);
    }
  }
  const ordered: Array<{ event: TraceEvent; depth: number }> = [];
  const visit = (id: string, depth: number) => {
    const node = nodes.get(id);
    if (!node) return;
    ordered.push({ event: node.event, depth });
    for (const child of node.children) {
      visit(child, depth + 1);
    }
  };
  for (const root of roots) {
    visit(root, 0);
  }
  return ordered;
}

export function collectToolCalls(events: TraceEvent[]): Array<{
  id: string;
  name: string;
  arguments: unknown;
  result?: unknown;
  error?: string;
  ts?: string;
}> {
  const results = new Map<string, { result?: unknown; error?: string }>();
  for (const event of events) {
    if (event.type === "tool_result" && event.span_id) {
      results.set(event.span_id, { result: event.result });
    }
    if (event.type === "tool_error" && event.span_id) {
      results.set(event.span_id, { error: String(event.error ?? "Unknown error") });
    }
  }
  return events
    .filter((event) => event.type === "tool_call")
    .map((event) => {
      const spanId = String(event.span_id ?? "");
      const outcome = results.get(spanId);
      return {
        id: spanId,
        name: String(event.tool_name ?? "unknown"),
        arguments: event.arguments,
        result: outcome?.result,
        error: outcome?.error,
        ts: event.ts,
      };
    });
}
