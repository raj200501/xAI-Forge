import { useCallback, useEffect, useMemo, useState } from "react";
import TraceList from "../components/TraceList";
import FiltersBar from "../components/FiltersBar";
import CommandPalette from "../components/CommandPalette";
import TracePage from "../pages/TracePage";
import LiveRunPage from "../pages/LiveRunPage";
import ComparePage from "../pages/ComparePage";
import DashboardPage from "../pages/DashboardPage";
import EvalsPage from "../pages/EvalsPage";
import ExperimentsPage from "../pages/ExperimentsPage";
import PerfPage from "../pages/PerfPage";
import ProvidersPlaygroundPage from "../pages/ProvidersPlaygroundPage";
import PoliciesPage from "../pages/PoliciesPage";
import {
  fetchManifests,
  fetchProviders,
  fetchTraceEvents,
  replayTrace,
  startRun,
  streamEvents,
} from "../lib/api";
import type { TraceEvent, TraceManifest } from "../types/trace";
import { filterManifests } from "../lib/trace";

const routes = [
  { key: "traces", label: "Traces" },
  { key: "live", label: "Live Run" },
  { key: "compare", label: "Compare" },
  { key: "dashboard", label: "Dashboard" },
  { key: "experiments", label: "Experiments" },
  { key: "evals", label: "Evals" },
  { key: "perf", label: "Perf Lab" },
  { key: "playground", label: "Playground" },
  { key: "policies", label: "Policies" },
] as const;

type RouteKey = (typeof routes)[number]["key"];

export default function App() {
  const [manifests, setManifests] = useState<TraceManifest[]>([]);
  const [providers, setProviders] = useState<string[]>(["heuristic"]);
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const [eventsByTrace, setEventsByTrace] = useState<Record<string, TraceEvent[]>>({});
  const [replaying, setReplaying] = useState(false);
  const [route, setRoute] = useState<RouteKey>("traces");
  const [filters, setFilters] = useState({
    query: "",
    provider: "all",
    durationMin: "",
    durationMax: "",
    toolCallsMin: "",
  });
  const [commandOpen, setCommandOpen] = useState(false);
  const [liveEvents, setLiveEvents] = useState<TraceEvent[]>([]);
  const [liveRunning, setLiveRunning] = useState(false);
  const [liveTraceId, setLiveTraceId] = useState<string | null>(null);
  const [compareLeft, setCompareLeft] = useState("");
  const [compareRight, setCompareRight] = useState("");

  const activeManifest = useMemo(
    () => manifests.find((manifest) => manifest.trace_id === activeTraceId) || null,
    [activeTraceId, manifests],
  );

  useEffect(() => {
    fetchManifests().then(setManifests).catch(console.error);
    fetchProviders().then(setProviders).catch(console.error);
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.getAttribute("contenteditable") === "true";
      if (event.key === "/" && !event.metaKey && !event.ctrlKey) {
        if (isTyping) return;
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const loadTrace = useCallback(
    async (traceId: string) => {
      setActiveTraceId(traceId);
      setRoute("traces");
      if (eventsByTrace[traceId]) return;
      const events = await fetchTraceEvents(traceId);
      setEventsByTrace((prev) => ({ ...prev, [traceId]: events }));
    },
    [eventsByTrace],
  );

  const handleReplay = useCallback(async () => {
    if (!activeTraceId) return;
    setReplaying(true);
    const events = await replayTrace(activeTraceId);
    setEventsByTrace((prev) => ({ ...prev, [activeTraceId]: events }));
    setReplaying(false);
  }, [activeTraceId]);

  const handleStartRun = useCallback(
    async (payload: { task: string; root: string; provider: string; allow_net: boolean }) => {
      setLiveEvents([]);
      setLiveRunning(true);
      setLiveTraceId(null);
      const response = await startRun(payload);
      await streamEvents(response, (event) => {
        setLiveEvents((prev) => [...prev, event]);
        if (event.type === "run_start") {
          setLiveTraceId(String(event.trace_id));
        }
        if (event.type === "run_end") {
          setLiveRunning(false);
          fetchManifests().then(setManifests).catch(console.error);
        }
      });
      setLiveRunning(false);
    },
    [],
  );

  const filteredManifests = useMemo(
    () => filterManifests(manifests, filters),
    [filters, manifests],
  );

  const activeEvents = activeTraceId ? eventsByTrace[activeTraceId] || [] : [];

  const compareLeftEvents = eventsByTrace[compareLeft] || [];
  const compareRightEvents = eventsByTrace[compareRight] || [];

  useEffect(() => {
    if (compareLeft && !eventsByTrace[compareLeft]) {
      fetchTraceEvents(compareLeft)
        .then((events) => setEventsByTrace((prev) => ({ ...prev, [compareLeft]: events })))
        .catch(console.error);
    }
  }, [compareLeft, eventsByTrace]);

  useEffect(() => {
    if (compareRight && !eventsByTrace[compareRight]) {
      fetchTraceEvents(compareRight)
        .then((events) => setEventsByTrace((prev) => ({ ...prev, [compareRight]: events })))
        .catch(console.error);
    }
  }, [compareRight, eventsByTrace]);

  return (
    <div className="app-shell">
      <CommandPalette
        open={commandOpen}
        onClose={() => setCommandOpen(false)}
        traces={manifests}
        activeTraceId={activeTraceId}
        onSelectTrace={(traceId) => loadTrace(traceId)}
        onStartRun={() => setRoute("live")}
        onReplay={handleReplay}
      />
      <aside className="sidebar">
        <div className="brand">
          <div>
            <h1>xAI-Forge</h1>
            <span>Flight Recorder</span>
          </div>
          <button className="ghost-button" type="button" onClick={() => setCommandOpen(true)}>
            / Command
          </button>
        </div>
        <nav>
          {routes.map((item) => (
            <button
              key={item.key}
              type="button"
              className={route === item.key ? "active" : ""}
              onClick={() => setRoute(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-section">
          <h3>Trace Archive</h3>
          <FiltersBar
            query={filters.query}
            provider={filters.provider}
            providers={providers}
            durationMin={filters.durationMin}
            durationMax={filters.durationMax}
            toolCallsMin={filters.toolCallsMin}
            onChange={setFilters}
          />
          <TraceList traces={filteredManifests} activeId={activeTraceId} onSelect={loadTrace} />
        </div>
      </aside>
      <main className="main">
        {route === "traces" && (
          <TracePage
            manifest={activeManifest}
            events={activeEvents}
            onReplay={handleReplay}
            replaying={replaying}
          />
        )}
        {route === "live" && (
          <LiveRunPage
            providers={providers}
            onStart={handleStartRun}
            events={liveEvents}
            running={liveRunning}
            traceId={liveTraceId}
            onOpenTrace={(traceId) => {
              loadTrace(traceId).catch(console.error);
              setRoute("traces");
            }}
          />
        )}
        {route === "compare" && (
          <ComparePage
            traces={manifests}
            leftId={compareLeft}
            rightId={compareRight}
            onSelectLeft={setCompareLeft}
            onSelectRight={setCompareRight}
            leftEvents={compareLeftEvents}
            rightEvents={compareRightEvents}
          />
        )}
        {route === "dashboard" && <DashboardPage />}
        {route === "experiments" && <ExperimentsPage />}
        {route === "evals" && <EvalsPage />}
        {route === "perf" && <PerfPage />}
        {route === "playground" && <ProvidersPlaygroundPage />}
        {route === "policies" && <PoliciesPage />}
      </main>
    </div>
  );
}
