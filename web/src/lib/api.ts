export async function fetchManifests() {
  const res = await fetch("/api/traces");
  if (!res.ok) throw new Error("Failed to fetch traces");
  return res.json();
}

export async function fetchTraceEvents(traceId: string) {
  const res = await fetch(`/api/traces/${traceId}/events`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function replayTrace(traceId: string) {
  const res = await fetch(`/api/replay/${traceId}`, {
    method: "POST",
  });
  if (!res.body) throw new Error("Missing stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const events: any[] = [];
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.replace("data:", "").trim();
      if (json) {
        events.push(JSON.parse(json));
      }
    }
  }
  return events;
}
