import type { TraceEvent, TraceManifest, ToolSpec } from "../types/trace";

const jsonHeaders = {
  "Content-Type": "application/json",
};

export async function fetchManifests(): Promise<TraceManifest[]> {
  const res = await fetch("/api/traces");
  if (!res.ok) throw new Error("Failed to fetch traces");
  return res.json();
}

export async function fetchTraceEvents(traceId: string): Promise<TraceEvent[]> {
  const res = await fetch(`/api/traces/${traceId}/events`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function fetchProviders(): Promise<string[]> {
  const res = await fetch("/api/providers");
  if (!res.ok) throw new Error("Failed to fetch providers");
  return res.json();
}

export async function fetchTools(): Promise<ToolSpec[]> {
  const res = await fetch("/api/tools");
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

export async function fetchEventSchema(): Promise<Record<string, unknown>> {
  const res = await fetch("/api/schema/events");
  if (!res.ok) throw new Error("Failed to fetch event schema");
  return res.json();
}

export async function replayTrace(traceId: string): Promise<TraceEvent[]> {
  const res = await fetch(`/api/replay/${traceId}`, {
    method: "POST",
    headers: jsonHeaders,
  });
  return collectStreamedEvents(res);
}

export async function startRun(payload: {
  task: string;
  root: string;
  provider: string;
  allow_net: boolean;
}): Promise<Response> {
  return fetch("/api/run", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
}

export async function collectStreamedEvents(res: Response): Promise<TraceEvent[]> {
  if (!res.body) throw new Error("Missing stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const events: TraceEvent[] = [];
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((segment) => segment.startsWith("data:"));
      if (!line) continue;
      const json = line.replace("data:", "").trim();
      if (json) {
        events.push(JSON.parse(json));
      }
    }
  }
  return events;
}

export async function streamEvents(
  res: Response,
  onEvent: (event: TraceEvent) => void,
): Promise<void> {
  if (!res.body) throw new Error("Missing stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((segment) => segment.startsWith("data:"));
      if (!line) continue;
      const json = line.replace("data:", "").trim();
      if (json) {
        onEvent(JSON.parse(json));
      }
    }
  }
}

export async function fetchExperiments(): Promise<Record<string, unknown>[]> {
  const res = await fetch("/api/experiments");
  if (!res.ok) throw new Error("Failed to fetch experiments");
  return res.json();
}

export async function fetchExperimentReport(name: string): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/experiments/${name}`);
  if (!res.ok) throw new Error("Failed to fetch experiment");
  return res.json();
}

export async function fetchReportList(kind: "evals" | "perf" | "experiments"): Promise<string[]> {
  const res = await fetch(`/api/reports/${kind}`);
  if (!res.ok) throw new Error("Failed to fetch reports");
  return res.json();
}

export async function fetchReport(kind: "evals" | "perf" | "experiments", name: string): Promise<any> {
  const res = await fetch(`/api/reports/${kind}/${name}`);
  if (!res.ok) throw new Error("Failed to fetch report");
  return res.json();
}

export async function fetchPlugins(): Promise<string[]> {
  const res = await fetch("/api/plugins");
  if (!res.ok) throw new Error("Failed to fetch plugins");
  return res.json();
}

export async function fetchPolicySummary(): Promise<Record<string, unknown>> {
  const res = await fetch("/api/policy/summary");
  if (!res.ok) throw new Error("Failed to fetch policy summary");
  return res.json();
}

export async function runGateway(payload: {
  provider: string;
  messages: { role: string; content: string }[];
}): Promise<Record<string, unknown>> {
  const res = await fetch("/api/gateway/run", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to run gateway");
  return res.json();
}
